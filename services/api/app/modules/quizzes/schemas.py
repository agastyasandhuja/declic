from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.recommendations.models import Identifier
from app.modules.recommendations.schemas import RequestModel


class QuizOption(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    option_id: Identifier
    text: str = Field(min_length=1, max_length=2000)


class QuizDefinition(BaseModel):
    """Server-only immutable instance input from the video/assessment producer."""

    model_config = ConfigDict(extra="ignore", frozen=True)
    quiz_id: Identifier
    revision: int = Field(ge=1)
    objective_ids: list[Identifier] = Field(min_length=1, max_length=10)
    prompt: str = Field(min_length=1, max_length=4000)
    options: list[QuizOption] = Field(min_length=2, max_length=8)
    correct_option_id: Identifier
    explanation: str = Field(min_length=1, max_length=4000)
    misconception_by_option: dict[str, str] = Field(default_factory=dict)
    source_refs: list[dict] = Field(default_factory=list)
    scope: Literal["private", "shared_generic"]
    owner_user_id: Identifier | None = None

    @model_validator(mode="after")
    def valid_answers(self):
        ids = {o.option_id for o in self.options}
        if len(ids) != len(self.options) or self.correct_option_id not in ids:
            raise ValueError("Quiz options must be unique and contain the answer key")
        if not set(self.misconception_by_option).issubset(ids):
            raise ValueError("Misconceptions must refer to defined options")
        if (self.scope == "private") != (self.owner_user_id is not None):
            raise ValueError("Invalid quiz ownership")
        return self

    def card(self, instance_id: str, video_ids: list[str]) -> dict:
        return self.model_dump(
            mode="json",
            include={
                "quiz_id",
                "revision",
                "objective_ids",
                "prompt",
                "options",
            },
        ) | {"quiz_instance_id": instance_id, "related_video_ids": video_ids}


class QuizCard(BaseModel):
    quiz_instance_id: str
    quiz_id: str
    revision: int
    objective_ids: list[str]
    prompt: str
    options: list[QuizOption]
    related_video_ids: list[str]


class AnswerRequest(RequestModel):
    session_id: Identifier
    selected_option_id: Identifier


class RecoveryRequest(RequestModel):
    session_id: Identifier
    reason: Literal["content_error", "submission_unavailable"]
    client_event_id: Identifier


class AnswerResponse(BaseModel):
    schema_version: Literal["1"] = "1"
    attempt_id: str
    accepted: bool
    correct: bool
    explanation: str
    scroll_unlocked: bool
    learning_revision: int
    recommendation_revision: int


class RecoveryResponse(BaseModel):
    schema_version: Literal["1"] = "1"
    accepted: bool
    graded: Literal[False] = False
    scroll_unlocked: bool
    recommendation_revision: int
