"""Demo Instagram login with encrypted reusable sessions and background catalog fill."""

import time
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.core import collections as tables
from app.core.dependencies import CurrentUser
from app.core.errors import APIError
from app.core.time import iso, new_id, utc_now
from app.modules.entertainment.instagram import (
    InstagramReelsProvider,
    make_instagram_client,
)
from app.modules.entertainment.instagram_connection import (
    LOGIN_ERRORS,
    SESSION_FIELDS,
    device_settings,
)
from app.modules.entertainment.instagram_login import (
    login_interactively,
    login_with_browser_session,
)
from app.modules.entertainment.pagination import batch_revision
from app.modules.entertainment.repository import storage_errors
from app.modules.entertainment.service import (
    CatalogFailure,
    CatalogService,
    normalized_items,
    playable,
)
from app.workers.queue import enqueue


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    username: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_.]+$")
    password: SecretStr = Field(min_length=1, max_length=1024)
    verification_code: SecretStr | None = Field(default=None, min_length=6, max_length=6)
    verification_method: Literal["totp"] = "totp"


class BrowserSessionLogin(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    username: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_.]+$")
    session_id: SecretStr = Field(min_length=31, max_length=16384)


class SocialConnections:
    def __init__(self, database, vault):
        self.database, self.vault = database, vault

    def get(self, owner):
        return self.database.read(
            lambda tx: tx.find_one(tables.connections, {"user_id": owner, "provider": "instagram"})
        )

    def public(self, owner):
        row = self.get(owner)
        return {
            "schema_version": "1",
            "status": row["status"] if row else "disconnected",
            "last_sync_at": row.get("last_sync_at") if row else None,
        }

    def connect(self, owner, body):
        query = {"user_id": owner, "provider": "instagram"}
        attempt_id = new_id()

        def begin(tx):
            row = tx.find_one(tables.connections, query)
            if row and row.get("last_attempt", 0) > time.time() - 30:
                raise APIError(
                    429, "LOGIN_COOLDOWN", "Wait 30 seconds before another login attempt"
                )
            tx.insert_if_absent(
                tables.connections, {**query, "status": "disconnected"}, list(query)
            )
            tx.update(
                tables.connections, query, {"last_attempt": time.time(), "attempt_id": attempt_id}
            )
            return row

        previous = self.database.run(owner, begin)
        saved = (
            self.vault.open(owner, "instagram", previous["sealed"])
            if previous and previous.get("sealed")
            else {}
        )
        # Fresh credential submission must not silently reuse a different account.
        client = make_instagram_client(
            device_settings(saved["session"]) if saved.get("session") else None
        )
        provider = InstagramReelsProvider(client)

        def read_code(_prompt):
            if "sms" in _prompt.casefold():
                raise APIError(
                    409,
                    "INSTAGRAM_LOCAL_VERIFICATION_REQUIRED",
                    "Complete SMS verification through the local interactive "
                    "or browser-session helper.",
                )
            if body.verification_code is None:
                raise APIError(
                    409,
                    "INSTAGRAM_TWO_FACTOR_REQUIRED",
                    "Instagram requested two-factor verification. Enter a current code and retry "
                    "manually, or connect through the local browser-session helper.",
                )
            return body.verification_code.get_secret_value()

        try:
            if isinstance(body, BrowserSessionLogin):
                verified = login_with_browser_session(
                    client, body.username, body.session_id.get_secret_value(), {}
                )
            else:
                verified = login_interactively(
                    client,
                    body.username,
                    body.password.get_secret_value(),
                    {},
                    read_code=read_code,
                    choose_method=lambda _prompt: body.verification_method,
                    expected_username=body.username,
                    allowed_methods={"totp"},
                )
            session = {key: value for key, value in verified.items() if key in SESSION_FIELDS}
            sealed = self.vault.seal(
                owner, "instagram", {"session": session, "cursor": None, "surface": "discover"}
            )
        except Exception as error:
            code, message = (
                (error.code, error.message)
                if isinstance(error, (APIError, CatalogFailure))
                else LOGIN_ERRORS.get(
                    type(error).__name__,
                    (
                        "INSTAGRAM_LOGIN_FAILED",
                        "Instagram login failed. Check the official app before retrying.",
                    ),
                )
            )
            # A rejected replacement cookie must not discard a working login.
            # Do not restore the earlier row: a concurrent disconnect/reconnect
            # may have intentionally changed it while verification was running.
            keep_previous = (
                isinstance(body, BrowserSessionLogin)
                and previous
                and previous.get("status") == "connected"
                and previous.get("sealed")
            )
            if not keep_previous:
                device = self.vault.seal(
                    owner, "instagram", {"session": device_settings(client.get_settings())}
                )
                self.database.run(
                    owner,
                    lambda tx: tx.update(
                        tables.connections,
                        {**query, "attempt_id": attempt_id},
                        {"status": "reconnect_required", "sealed": device},
                    ),
                )
            raise APIError(409, code, message) from None
        finally:
            provider.close()
        connection_id = new_id()

        def save(tx):
            current = tx.find_one(tables.connections, query)
            if current.get("attempt_id") != attempt_id:
                raise APIError(409, "CONNECTION_CHANGED", "Connection changed; retry login")
            tx.update(
                tables.connections,
                query,
                {
                    "status": "connected",
                    "sealed": sealed,
                    "connection_id": connection_id,
                    "connected_at": iso(utc_now()),
                    "last_sync_at": None,
                    "refresh_version": 0,
                    "retry_after": 0,
                    "playback_refresh_after": 0,
                    "playback_refreshed_video_id": None,
                },
            )
            if self.database.mongo is not None:
                self.database.mongo.entertainment_catalogs.delete_one(
                    {"user_id": owner}, session=tx.session
                )
            enqueue(
                tx,
                owner_user_id=owner,
                job_type="instagram.refresh",
                dedupe_key=connection_id,
                input_ref={"connection_id": connection_id},
            )

        self.database.run(owner, save)
        return self.public(owner)

    def disconnect(self, owner):
        def revoke(tx):
            tx.update(
                tables.connections,
                {"user_id": owner, "provider": "instagram"},
                {
                    "status": "disconnected",
                    "sealed": None,
                    "connection_id": new_id(),
                    "attempt_id": new_id(),
                },
            )
            self.database.mongo.entertainment_catalogs.delete_one(
                {"user_id": owner}, session=tx.session
            )

        self.database.run(owner, revoke)

    def schedule(self):
        rows = self.database.read(
            lambda tx: tx.find(
                tables.connections, {"provider": "instagram", "status": "connected"}, limit=100
            )
        )
        for row in rows:
            if row.get("retry_after", 0) > time.time():
                continue
            owner = row["user_id"]
            self.database.run(
                owner,
                lambda tx, owner=owner, row=row: enqueue(
                    tx,
                    owner_user_id=owner,
                    job_type="instagram.refresh",
                    dedupe_key=f"{row['connection_id']}:{int(time.time() // 30)}",
                    input_ref={"connection_id": row["connection_id"]},
                ),
            )

    @storage_errors
    def renew_playback(self, owner, video_id):
        """Renew one already-owned Reel; never fetch caller-selected provider IDs."""

        def claim(tx):
            catalog = (
                self.database.mongo.entertainment_catalogs.find_one(
                    {"user_id": owner}, session=tx.session
                )
                or {}
            )
            item = next(
                (item for item in catalog.get("items", []) if item["video_id"] == video_id), None
            )
            if item is None:
                raise CatalogFailure(404, "VIDEO_NOT_FOUND", "This clip is not in your catalog.")
            if item["provider"] != "instagram":
                if catalog.get("expires_at", utc_now()) <= utc_now():
                    raise CatalogFailure(
                        404, "CATALOG_NOT_FOUND", "No current catalog is connected to this account."
                    )
                if playable(item, utc_now()):
                    return None, item
                raise CatalogFailure(
                    410, "PLAYBACK_UNAVAILABLE", "This clip is unavailable or expired."
                )
            row = tx.find_one(
                tables.connections,
                {"user_id": owner, "provider": "instagram", "status": "connected"},
            )
            if not row:
                raise CatalogFailure(
                    409, "INSTAGRAM_RECONNECT_REQUIRED", "Reconnect Instagram to refresh this clip."
                )
            if row.get("retry_after", 0) > time.time():
                raise CatalogFailure(
                    503,
                    "INSTAGRAM_RATE_LIMITED",
                    "Instagram is cooling down. Keep watching loaded clips and retry shortly.",
                )
            if row.get("playback_refresh_after", 0) > time.time():
                if row.get("playback_refreshed_video_id") == video_id and playable(item, utc_now()):
                    return None, item
                raise CatalogFailure(
                    503,
                    "INSTAGRAM_BUSY",
                    "A clip was just refreshed. Retry shortly or skip this clip.",
                )
            tx.update(
                tables.connections,
                {"user_id": owner, "provider": "instagram", "connection_id": row["connection_id"]},
                {"playback_refresh_after": time.time() + 30, "playback_refreshed_video_id": None},
            )
            return row, item

        row, item = self.database.run(owner, claim)
        if row is None:
            return item["playback"]
        identifier, version = row["connection_id"], row.get("refresh_version", 0)
        saved = self.vault.open(owner, "instagram", row["sealed"])
        provider = InstagramReelsProvider(
            make_instagram_client(saved["session"]), surface=saved.get("surface", "discover")
        )
        try:
            fresh = normalized_items([provider.refresh(item["provider_video_id"])])[0]
            if (
                fresh["video_id"] != video_id
                or fresh["provider_video_id"] != item["provider_video_id"]
                or fresh["provider"] != "instagram"
                or not playable(fresh, utc_now())
            ):
                raise CatalogFailure(
                    410, "PLAYBACK_UNAVAILABLE", "Instagram could not renew this clip. Skip it."
                )
            session = {
                key: value
                for key, value in provider.client.get_settings().items()
                if key in SESSION_FIELDS
            }
        except CatalogFailure as error:

            def record_failure(tx, error=error):
                current = tx.find_one(
                    tables.connections,
                    {
                        "user_id": owner,
                        "provider": "instagram",
                        "connection_id": identifier,
                        "status": "connected",
                    },
                )
                if current is not None and current.get("refresh_version", 0) == version:
                    changes = {"retry_after": time.time() + getattr(error, "retry_after", 30)}
                    if error.code == "INSTAGRAM_RECONNECT_REQUIRED":
                        changes["status"] = "reconnect_required"
                    tx.update(
                        tables.connections,
                        {"user_id": owner, "provider": "instagram", "connection_id": identifier},
                        changes,
                    )

            self.database.run(owner, record_failure)
            raise
        finally:
            provider.close()
        sealed = self.vault.seal(owner, "instagram", {**saved, "session": session})

        def publish(tx):
            current = tx.find_one(
                tables.connections,
                {
                    "user_id": owner,
                    "provider": "instagram",
                    "connection_id": identifier,
                    "status": "connected",
                },
            )
            if current is None:
                raise CatalogFailure(
                    409,
                    "INSTAGRAM_RECONNECT_REQUIRED",
                    "Instagram connection changed. Reconnect if needed.",
                )
            if current.get("refresh_version", 0) != version:
                raise CatalogFailure(
                    503, "INSTAGRAM_BUSY", "Your feed refreshed during this request. Retry shortly."
                )
            collection = self.database.mongo.entertainment_catalogs
            catalog = collection.find_one({"user_id": owner}, session=tx.session) or {}
            items = catalog.get("items", [])
            if not any(value["video_id"] == video_id for value in items):
                raise CatalogFailure(
                    404, "VIDEO_NOT_FOUND", "This clip is no longer in your catalog."
                )
            items = normalized_items(
                [fresh if value["video_id"] == video_id else value for value in items]
            )
            now = utc_now()
            collection.replace_one(
                {"user_id": owner},
                {
                    **catalog,
                    "items": items,
                    "revision": batch_revision(items),
                    "updated_at": now,
                    "expires_at": now + timedelta(minutes=10),
                },
                session=tx.session,
            )
            tx.update(
                tables.connections,
                {"user_id": owner, "provider": "instagram", "connection_id": identifier},
                {
                    "sealed": sealed,
                    "refresh_version": version + 1,
                    "playback_refreshed_video_id": video_id,
                },
            )
            return fresh["playback"]

        return self.database.run(owner, publish)

    def refresh(self, context):
        owner, identifier = context.owner_user_id, context.input_ref["connection_id"]
        row = self.get(owner)
        if not row or row.get("connection_id") != identifier or row["status"] != "connected":
            return {"state": "revoked"}
        if row.get("retry_after", 0) > time.time():
            return {"state": "cooldown"}
        version = row.get("refresh_version", 0)
        saved = self.vault.open(owner, "instagram", row["sealed"])
        provider = InstagramReelsProvider(
            make_instagram_client(saved["session"]), surface=saved.get("surface", "discover")
        )
        try:
            page = provider.read_page(saved.get("cursor"))
            session = {
                key: value
                for key, value in provider.client.get_settings().items()
                if key in SESSION_FIELDS
            }
        except CatalogFailure as error:
            changes = {"retry_after": time.time() + getattr(error, "retry_after", 60)}
            if error.code == "INSTAGRAM_RECONNECT_REQUIRED":
                changes["status"] = "reconnect_required"

            def record_failure(tx):
                current = tx.find_one(
                    tables.connections,
                    {
                        "user_id": owner,
                        "provider": "instagram",
                        "connection_id": identifier,
                        "status": "connected",
                    },
                )
                if current is not None and current.get("refresh_version", 0) == version:
                    tx.update(
                        tables.connections,
                        {"user_id": owner, "provider": "instagram", "connection_id": identifier},
                        changes,
                    )

            self.database.run(owner, record_failure)
            return {"state": "cooldown", "error_code": error.code}
        finally:
            provider.close()
        if not context.heartbeat():
            raise RuntimeError("Lease lost")
        sealed = self.vault.seal(
            owner,
            "instagram",
            {
                "session": session,
                "cursor": page.next_cursor,
                "surface": saved.get("surface", "discover"),
            },
        )

        def publish(tx):
            current = tx.find_one(
                tables.connections,
                {
                    "user_id": owner,
                    "provider": "instagram",
                    "connection_id": identifier,
                    "status": "connected",
                },
            )
            if current is None:
                return {"state": "revoked"}
            if current.get("refresh_version", 0) != version:
                return {"state": "superseded"}
            collection = self.database.mongo.entertainment_catalogs
            old = collection.find_one({"user_id": owner}, session=tx.session) or {}
            now = utc_now()
            merged = {
                item["video_id"]: item for item in old.get("items", []) if playable(item, now)
            }
            merged.update({item["video_id"]: item for item in page.items})
            items = normalized_items(list(merged.values())[-100:])
            collection.replace_one(
                {"user_id": owner},
                {
                    "schema_version": "1",
                    "user_id": owner,
                    "items": items,
                    "revision": batch_revision(items),
                    "updated_at": now,
                    "expires_at": now + timedelta(minutes=10),
                },
                upsert=True,
                session=tx.session,
            )
            tx.update(
                tables.connections,
                {"user_id": owner, "provider": "instagram"},
                {
                    "sealed": sealed,
                    "last_sync_at": iso(now),
                    "refresh_version": version + 1,
                    "retry_after": 0,
                },
            )
            return {"count": len(items)}

        return self.database.run(owner, publish)


class ConnectedCatalogService(CatalogService):
    """Keep feed reads cached; renew known Instagram media only on explicit retry."""

    def __init__(self, repository, social, **kwargs):
        super().__init__(repository, **kwargs)
        self.social = social

    def resolve_playback(self, video_id, user):
        # Feed playback uses cached URLs directly. This endpoint is an explicit
        # recovery request, including CDN failures before the advertised expiry.
        # renew_playback preserves cached non-Instagram items and bounds retries.
        return self.social.renew_playback(user["user_id"], video_id)


def create_router(social):
    router = APIRouter(prefix="/v1/instagram", tags=["instagram"])

    @router.get("/connection")
    def status(user: CurrentUser):
        return social.public(user.user_id)

    @router.post("/connect", status_code=202)
    def connect(user: CurrentUser, body: Login):
        return social.connect(user.user_id, body)

    @router.post("/browser-session", status_code=202)
    def browser_session(user: CurrentUser, body: BrowserSessionLogin):
        return social.connect(user.user_id, body)

    @router.delete("/connection", status_code=204)
    def disconnect(user: CurrentUser):
        social.disconnect(user.user_id)
        return Response(status_code=204)

    return router
