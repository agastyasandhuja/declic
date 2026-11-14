from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.modules.recommendations.models import Identifier


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionRequest(RequestModel):
    resume_session_id: Identifier | None = None
    refresh_unseen: bool = False


class GateRequest(RequestModel):
    quiz_instance_id: Identifier
    item_id: Identifier


class PlaybackPayload(RequestModel):
    position_ms: Annotated[int, Field(strict=True, ge=0, le=86_400_000)] = 0
    visible_watch_ms: Annotated[int, Field(strict=True, ge=0, le=86_400_000)] = 0


class PlaybackEvent(RequestModel):
    event_id: Identifier
    session_id: Identifier
    item_id: Identifier
    event_type: Literal[
        "playback_started",
        "playback_progress",
        "playback_completed",
        "video_skipped",
        "playback_failed",
        "app_backgrounded",
        "app_foregrounded",
    ]
    client_occurred_at: AwareDatetime
    payload: PlaybackPayload = Field(default_factory=PlaybackPayload)


EventBatch = Annotated[list[PlaybackEvent], Field(min_length=1, max_length=100)]


class SessionResponse(BaseModel):
    schema_version: Literal["1"] = "1"
    session_id: str
    started_at: AwareDatetime
    last_active_at: AwareDatetime
    active_view_seconds: float
    study_ratio_target: float
    recommendation_revision: int
    pending_quiz_instance_id: str | None


class GateResponse(BaseModel):
    schema_version: Literal["1"] = "1"
    session_id: str
    pending_quiz_instance_id: str | None
    scroll_locked: bool
    recommendation_revision: int


class EventRejection(BaseModel):
    event_id: str
    code: str


class EventResponse(BaseModel):
    schema_version: Literal["1"] = "1"
    accepted_event_ids: list[str]
    rejected: list[EventRejection]
