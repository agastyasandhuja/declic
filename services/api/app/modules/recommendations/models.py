"""Internal read projections, NOT replacements for producer-owned wire schemas.

Adapters map academics/entertainment/video public services to these inputs.
No private documents, provider headers, or answer keys belong in these models.
"""

from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]


def https_only(url: HttpUrl) -> HttpUrl:
    if url.scheme != "https" or url.username or url.password:
        raise ValueError("Playback references require HTTPS without embedded credentials")
    return url


HTTPSURL = Annotated[HttpUrl, AfterValidator(https_only)]


class ReadModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, allow_inf_nan=False)


class Playback(ReadModel):
    kind: Literal["mp4", "hls", "embed"]
    asset_id: Identifier
    url: HTTPSURL
    expires_at: AwareDatetime | None = None
    mime_type: str | None = None

    def playable(self, now: datetime) -> bool:
        return self.expires_at is None or (self.expires_at - now).total_seconds() > 30


class Creator(ReadModel):
    handle: str | None = None
    display_name: str | None = None
    attribution_url: HTTPSURL | None = None


class EntertainmentCandidate(ReadModel):
    schema_version: Literal["1"] = "1"
    video_id: Identifier
    provider: Literal["tiktok", "instagram", "fixture"]
    provider_video_id: Identifier
    source_url: HTTPSURL | None = None
    creator: Creator = Field(default_factory=Creator)
    caption: str = Field(default="", max_length=10000)
    like_count: int | None = Field(default=None, strict=True, ge=0, le=9007199254740991)
    comment_count: int | None = Field(default=None, strict=True, ge=0, le=9007199254740991)
    duration_seconds: float | None = Field(default=None, gt=0, le=86400)
    playback: Playback
    thumbnail_url: HTTPSURL | None = None
    acquired_at: AwareDatetime
    availability: Literal["ready", "unavailable", "needs_refresh"]
    acquisition_mode: Literal["live", "cached", "fixture"]


class ObjectiveCandidate(ReadModel):
    user_id: Identifier
    course_id: Identifier
    course_title: str
    objective_id: Identifier
    title: str
    level: str
    language: str
    notation: str
    current_unit: bool = False
    prerequisite_objective_ids: list[Identifier] = Field(default_factory=list)
    assessment_scope_status: Literal["explicit", "inferred", "user_confirmed", "unknown"] = (
        "unknown"
    )
    assessment_evidence_status: Literal["explicit", "inferred", "user_confirmed", "unknown"] = (
        "unknown"
    )
    assessment_date: date | None = None
    assessment_timestamp: AwareDatetime | None = None
    timezone: str = "UTC"

    @model_validator(mode="after")
    def validate_zone(self):
        ZoneInfo(self.timezone)
        return self


class VariantCandidate(ReadModel):
    video_id: Identifier
    objective_id: Identifier
    format_id: Literal[
        "dialogue_gameplay",
        "visual_explainer",
        "space_explainer",
        "math_explainer",
        "worked_example",
        "misconception",
        "analogy_story",
    ]
    teaching_approach: str
    level: str
    language: str
    notation: str
    scope: Literal["private", "shared_generic"]
    owner_user_id: Identifier | None = None
    status: Literal[
        "planned",
        "queued",
        "scripting",
        "voicing",
        "rendering",
        "validating",
        "ready",
        "failed",
    ]
    title: str
    learning_goal: str
    duration_seconds: float | None = Field(default=None, ge=0)
    playback: Playback | None = None
    thumbnail_url: HTTPSURL | None = None
    captions_ref: str | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if (self.scope == "private") != (self.owner_user_id is not None):
            raise ValueError("Private videos require an owner; shared videos must not have one")
        return self

    def eligible(self, user_id: str, objective: ObjectiveCandidate, now: datetime) -> bool:
        return (
            objective.user_id == user_id
            and self.status == "ready"
            and (self.scope == "shared_generic" or self.owner_user_id == user_id)
            and self.objective_id == objective.objective_id
            and (self.level, self.language, self.notation)
            == (objective.level, objective.language, objective.notation)
            and self.duration_seconds is not None
            and 30 <= self.duration_seconds <= 60
            and self.playback is not None
            and self.playback.playable(now)
        )

    def public_summary(self) -> dict:
        # Explicit allow-list: do not leak originating private lesson request, owner,
        # source references, generation prompts, or internal quality diagnostics.
        return self.model_dump(
            mode="json",
            include={
                "video_id",
                "objective_id",
                "format_id",
                "teaching_approach",
                "level",
                "language",
                "notation",
                "scope",
                "status",
                "title",
                "learning_goal",
                "duration_seconds",
                "playback",
                "thumbnail_url",
                "captions_ref",
            },
        ) | {"schema_version": "1", "asset_id": self.playback.asset_id if self.playback else None}
