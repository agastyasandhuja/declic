"""Persistent owner-scoped demo Canvas connection and durable sync requests."""

import hashlib
from typing import Annotated

from fastapi import APIRouter, Header, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.core import collections as tables
from app.core import idempotency
from app.core.dependencies import CurrentUser
from app.core.errors import APIError
from app.core.time import iso, new_id, utc_now
from app.modules.canvas.client.http import CanvasAuthError, CanvasClient, CanvasError
from app.modules.canvas.config import Secret
from app.workers.queue import enqueue


class CanvasToken(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    token: SecretStr = Field(min_length=10, max_length=4096)


class Connections:
    def __init__(self, database, vault, origin, client_factory=CanvasClient):
        self.database, self.vault = database, vault
        self.origin, self.client_factory = origin, client_factory

    def get(self, owner):
        return self.database.read(
            lambda tx: tx.find_one(tables.connections, {"user_id": owner, "provider": "canvas"}),
        )

    def public(self, owner):
        row = self.get(owner)
        return {
            "schema_version": "1",
            "institution_origin": self.origin,
            **(
                {key: row.get(key) for key in ("connection_id", "status", "last_sync_at", "job_id")}
                if row
                else {"status": "disconnected"}
            ),
        }

    def connect(self, owner, token, key=None):
        key = key or new_id()
        request = {"token_hash": hashlib.sha256(token.encode()).hexdigest()}
        attempt_id = new_id()
        query = {"user_id": owner, "provider": "canvas"}

        def begin(tx):
            prior = idempotency.lookup(tx, owner, "canvas/token", key, request)
            if prior is not None:
                return prior
            tx.insert_if_absent(
                tables.connections, {**query, "status": "disconnected"}, list(query)
            )
            tx.update(tables.connections, query, {"attempt_id": attempt_id})
            return None

        prior = self.database.run(owner, begin)
        if prior is not None:
            return prior
        try:
            identity = self.client_factory(self.origin, Secret(token)).get(
                "/api/v1/users/self/profile"
            )
            if not isinstance(identity, dict) or not identity.get("id"):
                raise CanvasError("Invalid profile")
        except CanvasAuthError:
            raise APIError(422, "CANVAS_TOKEN_REJECTED", "Canvas rejected this token") from None
        except CanvasError:
            raise APIError(
                503, "CANVAS_UNAVAILABLE", "Unable to verify Canvas; retry shortly", retryable=True
            ) from None
        connection_id = new_id()
        sealed = self.vault.seal(owner, "canvas", {"token": token})

        def save(tx):
            prior = idempotency.lookup(tx, owner, "canvas/token", key, request)
            if prior is not None:
                return prior
            current = tx.find_one(tables.connections, query)
            if not current or current.get("attempt_id") != attempt_id:
                raise APIError(409, "CONNECTION_CHANGED", "Connection changed; retry connecting")
            tx.update(
                tables.connections,
                query,
                {
                    "connection_id": connection_id,
                    "status": "connected",
                    "sealed": sealed,
                    "institution_origin": self.origin,
                    "last_sync_at": None,
                    "connected_at": iso(utc_now()),
                },
            )
            job_id = enqueue(
                tx,
                owner_user_id=owner,
                job_type="canvas.sync",
                dedupe_key=connection_id,
                input_ref={"connection_id": connection_id},
            )
            tx.update(tables.connections, query, {"job_id": job_id})
            response = {
                "schema_version": "1",
                "institution_origin": self.origin,
                "connection_id": connection_id,
                "status": "connected",
                "last_sync_at": None,
                "job_id": job_id,
                "state": "queued",
            }
            idempotency.remember(tx, owner, "canvas/token", key, request, response)
            return response

        return self.database.run(owner, save)

    def sync(self, owner, key):
        def queue(tx):
            row = tx.find_one(tables.connections, {"user_id": owner, "provider": "canvas"})
            if not row or row["status"] != "connected":
                raise APIError(409, "CANVAS_DISCONNECTED", "Connect Canvas before syncing")
            job_id = enqueue(
                tx,
                owner_user_id=owner,
                job_type="canvas.sync",
                dedupe_key=key,
                input_ref={"connection_id": row["connection_id"]},
            )
            tx.update(
                tables.connections, {"user_id": owner, "provider": "canvas"}, {"job_id": job_id}
            )
            return {"schema_version": "1", "job_id": job_id, "state": "queued"}

        return self.database.run(owner, queue)

    def disconnect(self, owner):
        self.database.run(
            owner,
            lambda tx: tx.update(
                tables.connections,
                {"user_id": owner, "provider": "canvas"},
                {
                    "status": "disconnected",
                    "sealed": None,
                    "connection_id": new_id(),
                    "attempt_id": new_id(),
                },
            ),
        )

    def require_current(self, owner, connection_id, tx=None):
        row = (
            tx.find_one(tables.connections, {"user_id": owner, "provider": "canvas"})
            if tx is not None
            else self.get(owner)
        )
        if not row or row["status"] != "connected" or row["connection_id"] != connection_id:
            raise PermissionError("Canvas connection was revoked")
        return row

    def client(self, owner, connection_id):
        row = self.require_current(owner, connection_id)
        token = self.vault.open(owner, "canvas", row["sealed"])["token"]
        return self.client_factory(row["institution_origin"], Secret(token))


def create_router(connections):
    router = APIRouter(prefix="/v1/canvas", tags=["canvas"])

    @router.get("/connection")
    def status(user: CurrentUser):
        return connections.public(user.user_id)

    @router.post("/token", status_code=202)
    def connect(
        user: CurrentUser,
        body: CanvasToken,
        idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
    ):
        return connections.connect(user.user_id, body.token.get_secret_value(), idempotency_key)

    @router.post("/sync", status_code=202)
    def sync(
        user: CurrentUser, idempotency_key: Annotated[str, Header(min_length=1, max_length=128)]
    ):
        return connections.sync(user.user_id, idempotency_key)

    @router.delete("/connection", status_code=204)
    def disconnect(user: CurrentUser):
        connections.disconnect(user.user_id)
        return Response(status_code=204)

    return router
