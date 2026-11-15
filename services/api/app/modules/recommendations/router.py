from typing import Annotated

from fastapi import APIRouter, Header, Query, Request

from app.core.dependencies import CurrentUser
from app.modules.recommendations.models import Identifier
from app.modules.recommendations.responses import FeedResponse
from app.modules.recommendations.schemas import (
    BootstrapRequest,
    EventBatch,
    EventResponse,
    GateRequest,
    GateResponse,
    SessionRequest,
    SessionResponse,
)

router = APIRouter(prefix="/v1/feed", tags=["feed"])


@router.post("/sessions", response_model=SessionResponse)
def sessions(body: SessionRequest, request: Request, user: CurrentUser):
    return request.app.state.feed.start_session(user.user_id, body.resume_session_id,
                                                refresh_unseen=body.refresh_unseen)


@router.post("/bootstrap", response_model=FeedResponse, response_model_exclude_none=False)
def bootstrap(
    body: BootstrapRequest,
    request: Request,
    user: CurrentUser,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
):
    return request.app.state.feed.bootstrap(
        user.user_id, body.limit, body.preferred_video_ids, idempotency_key
    )


@router.get("", response_model=FeedResponse, response_model_exclude_none=False)
def feed(
    request: Request,
    user: CurrentUser,
    session_id: Annotated[Identifier, Query()],
    cursor: Annotated[Identifier | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    return request.app.state.feed.get_feed(user.user_id, session_id, cursor, limit)


@router.post("/events", response_model=EventResponse)
def events(body: EventBatch, request: Request, user: CurrentUser):
    return request.app.state.playback_events.record(user.user_id, body)


@router.post("/sessions/{session_id}/quiz-gate", response_model=GateResponse)
def gate(session_id: Identifier, body: GateRequest, request: Request, user: CurrentUser):
    return request.app.state.feed.activate_gate(
        user.user_id,
        session_id,
        body.quiz_instance_id,
        body.item_id,
    )
