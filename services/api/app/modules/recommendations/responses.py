from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field

from app.modules.quizzes.schemas import QuizCard
from app.modules.recommendations.models import EntertainmentCandidate, Playback


class StudySummary(BaseModel):
    schema_version: Literal["1"]
    video_id: str
    objective_id: str
    format_id: str
    teaching_approach: str
    level: str
    language: str
    notation: str
    scope: Literal["private", "shared_generic"]
    status: Literal["ready"]
    title: str
    learning_goal: str
    duration_seconds: float = Field(ge=30, le=60)
    asset_id: str
    playback: Playback
    thumbnail_url: str | None
    captions_ref: str | None


class CourseContext(BaseModel):
    course_id: str
    title: str
    objective_id: str


class ItemBase(BaseModel):
    item_id: str
    inserted_at: AwareDatetime
    reason_codes: list[str]


class EntertainmentItem(ItemBase):
    kind: Literal["entertainment_video"]
    video: EntertainmentCandidate


class StudyItem(ItemBase):
    kind: Literal["study_video"]
    video: StudySummary
    course_context: CourseContext
    reason_text: str
    constraint_relaxations: list[str] = Field(default_factory=list)


class QuizItem(ItemBase):
    kind: Literal["quiz"]
    quiz: QuizCard


FeedItem = Annotated[EntertainmentItem | StudyItem | QuizItem, Field(discriminator="kind")]


class Availability(BaseModel):
    study: Literal["ready", "unavailable"]
    entertainment: Literal["ready", "unavailable"]


class FeedResponse(BaseModel):
    schema_version: Literal["1"] = "1"
    session_id: str
    recommendation_revision: int
    items: list[FeedItem]
    next_cursor: str | None
    pending_quiz_instance_id: str | None
    availability: Availability | None = None
    demo_mode: bool | None = None
