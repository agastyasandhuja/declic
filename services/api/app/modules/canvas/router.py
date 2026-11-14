"""Canvas connection routes using shared app identity and local job execution."""
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict

from app.core.dependencies import CurrentUser
from app.core.errors import APIError

from ..curriculum.jobs import DuplicateJob
from ..curriculum.router import IdempotencyKey
from ..curriculum.sources import CanvasSourceResolver
from ..curriculum.store import LOCK
from .client.http import CanvasAuthError, CanvasClient
from .oauth import CanvasOAuthError, StateStore, build_authorization_url, exchange_code


class Connect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution: str


def create_router(settings, academics, jobs, *, app_return_url=None, exchange=exchange_code):
    router = APIRouter(prefix="/v1/canvas", tags=["canvas"])
    states = StateStore()
    lock = RLock()
    connections = {}
    pending = {}

    def connection(owner):
        if owner not in connections and settings.dev_token and owner == settings.dev_token_app_user_id:
            connections[owner] = (
                dict(connection_id=str(uuid4()), user_id=owner,
                     institution_origin=settings.institution_origin, external_user_id=None,
                     mode="developer_token", status="connected", last_sync_at=None),
                settings.developer_token_for(owner),
            )
        return connections.get(owner)

    @router.get("/connection")
    def get_connection(user: CurrentUser):
        with lock:
            record = connection(user.user_id)
            return {"schema_version": "1", **(record[0] if record else {"status": "disconnected"})}

    @router.post("/connect")
    def connect(user: CurrentUser, body: Connect):
        if body.institution != settings.institution_origin:
            raise APIError(422, "UNKNOWN_INSTITUTION", "Unsupported Canvas institution")
        if not settings.oauth_configured or not app_return_url:
            raise APIError(503, "OAUTH_UNAVAILABLE", "Canvas OAuth is unavailable")
        with lock:
            previous = pending.get(user.user_id)
            if previous:
                try:
                    states.consume(previous)
                except CanvasOAuthError:
                    pass
            state = states.issue(user.user_id)
            pending[user.user_id] = state
        return {"schema_version": "1", "authorization_url": build_authorization_url(settings, state)}

    @router.get("/callback")
    def callback(state: str = Query(max_length=128), code: str = Query(max_length=2048)):
        try:
            with lock:
                owner = states.consume(state)
            tokens = exchange(settings, code)
            with LOCK, lock:
                if pending.get(owner) != state:
                    raise CanvasOAuthError("session superseded")
                pending.pop(owner)
                connections[owner] = (
                    dict(connection_id=str(uuid4()), user_id=owner,
                         institution_origin=settings.institution_origin,
                         external_user_id=tokens.external_user_id, mode="oauth",
                         status="connected", last_sync_at=None),
                    tokens.access_token,
                )
        except CanvasOAuthError:
            raise APIError(400, "OAUTH_FAILED", "Canvas sign-in failed") from None
        return RedirectResponse(app_return_url, status_code=303, headers={"Referrer-Policy": "no-referrer"})

    @router.delete("/connection", status_code=204)
    def disconnect(user: CurrentUser):
        with LOCK, lock:
            previous = pending.pop(user.user_id, None)
            if previous:
                try:
                    states.consume(previous)
                except CanvasOAuthError:
                    pass
            connections[user.user_id] = None
        return Response(status_code=204)

    @router.post("/sync", status_code=202)
    def sync(user: CurrentUser, background: BackgroundTasks, idempotency_key: IdempotencyKey):
        owner = user.user_id
        with lock:
            record = connection(owner)
            if record is not None and record[0]["status"] == "reconnect_required":
                raise APIError(409, "CANVAS_RECONNECT_REQUIRED", "Reconnect Canvas before syncing")
            if record is None:
                raise APIError(409, "CANVAS_DISCONNECTED", "Connect Canvas before syncing")
        info, token = record

        def still_connected():
            with lock:
                return connections.get(owner) is record

        def run():
            if not still_connected():
                raise PermissionError("Canvas disconnected")
            resolver = CanvasSourceResolver(
                CanvasClient(settings.institution_origin, token), owner_user_id=owner
            )
            try:
                profile = academics.import_profile(owner, resolver, publication_guard=still_connected)
            except CanvasAuthError:
                with lock:
                    if connections.get(owner) is record:
                        info["status"] = "reconnect_required"
                raise
            with lock:
                if connections.get(owner) is record:
                    info["last_sync_at"] = datetime.now(timezone.utc).isoformat()
            return profile

        try:
            return jobs.enqueue(owner, "canvas_sync", idempotency_key, info["connection_id"], background, run)
        except DuplicateJob:
            raise APIError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key already used") from None

    return router
