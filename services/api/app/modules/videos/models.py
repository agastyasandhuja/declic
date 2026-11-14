from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")]
Text = Annotated[str, Field(min_length=1, max_length=1000)]
Format = Literal["dialogue_gameplay", "visual_explainer"]


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Fact(Record):
    fact_id: Identifier
    statement: Text


class Brief(Record):
    schema_version: Literal["1"] = "1"
    brief_id: Identifier
    lesson_request_id: Identifier
    objective_id: Identifier
    title: Annotated[str, Field(min_length=1, max_length=90)]
    learning_goal: Text
    subject: Text
    level: Text
    language: Literal["en"] = "en"
    notation: Text
    assumed_knowledge: list[Text] = Field(max_length=10)
    must_cover: list[Identifier] = Field(min_length=1, max_length=12)
    must_not_claim: list[Text] = Field(max_length=12)
    approved_facts: list[Fact] = Field(min_length=1, max_length=20)
    input_values: list[int] = Field(min_length=2, max_length=5)
    format_id: Format
    teaching_approach: Identifier
    target_duration_seconds: int = Field(default=45, ge=30, le=60)
    scope: Literal["private", "shared_generic_candidate"] = "private"
    owner_user_id: Identifier | None = None
    template_version: str = "1.0.0"

    @model_validator(mode="after")
    def consistent(self):
        if self.scope == "private" and not self.owner_user_id:
            raise ValueError("Private briefs require an owner")
        ids = [f.fact_id for f in self.approved_facts]
        if len(set(ids)) != len(ids) or not set(self.must_cover) <= set(ids):
            raise ValueError("Required facts must resolve uniquely")
        return self

    def teaching_payload(self):
        return self.model_dump(exclude={"owner_user_id", "scope", "brief_id", "lesson_request_id"})

    def generation_key(self, recipe: dict):
        return digest(
            {"brief": self.model_dump(exclude={"brief_id", "lesson_request_id"}), "recipe": recipe}
        )


class Segment(Record):
    segment_id: Identifier
    speaker_role: Literal["peter", "stewie", "narrator"]
    spoken_text: Annotated[str, Field(min_length=1, max_length=600)]
    fact_ids: list[Identifier] = Field(max_length=12)
    delivery: Literal["neutral", "curious", "sarcastic", "emphatic"] = "neutral"


class Cue(Record):
    segment_id: Identifier
    phrase: Annotated[str, Field(min_length=1, max_length=120)]
    occurrence: int = Field(default=0, ge=0, le=10)
    edge: Literal["start", "end"] = "start"


class Event(Record):
    action: Literal["intro", "save", "reverse", "advance", "finish"]
    node: int = Field(ge=0, le=4)
    cue: Cue


class Storyboard(Record):
    schema_version: Literal["1"] = "1"
    title: Annotated[str, Field(min_length=1, max_length=90)]
    segments: list[Segment] = Field(min_length=3, max_length=16)
    events: list[Event] = Field(min_length=3, max_length=20)

    def validate_for(self, brief: Brief):
        ids = [s.segment_id for s in self.segments]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate segment IDs")
        facts = {f.fact_id for f in brief.approved_facts}
        covered = {f for s in self.segments for f in s.fact_ids}
        if not set(brief.must_cover) <= covered or not covered <= facts:
            raise ValueError("Missing or invented fact coverage")
        roles = {s.speaker_role for s in self.segments}
        if brief.format_id == "visual_explainer" and roles != {"narrator"}:
            raise ValueError("Explainer requires narrator")
        if brief.format_id == "dialogue_gameplay" and roles != {"peter", "stewie"}:
            raise ValueError(
                "Dialogue requires both characters and forbids narrator: EVERY segment must use "
                f"speaker_role peter or stewie; got {sorted(roles)}. "
                "Stewie narrates all demonstrations."
            )
        if not 75 <= sum(len(s.spoken_text.split()) for s in self.segments) <= 155:
            raise ValueError("Plan 75–155 words for a 30–60 second lesson")
        segments = {s.segment_id: s for s in self.segments}
        expected = (
            [("intro", 0)]
            + [
                (a, n)
                for n in range(len(brief.input_values))
                for a in ("save", "reverse", "advance")
            ]
            + [("finish", len(brief.input_values) - 1)]
        )
        if [(e.action, e.node) for e in self.events] != expected:
            raise ValueError(
                "Trace must save, reverse, advance every node in order, then finish. "
                f"Exact (action, zero-based node index) sequence: {expected}"
            )
        for e in self.events:
            if e.cue.segment_id not in segments:
                raise ValueError("Unknown cue segment")
            text = segments[e.cue.segment_id].spoken_text
            if text.count(e.cue.phrase) <= e.cue.occurrence:
                raise ValueError("Cue phrase does not resolve")
        return self


class SceneSource(Record):
    source: Annotated[str, Field(min_length=30, max_length=40000)]


class ContentReview(Record):
    passed: bool
    issues: list[Annotated[str, Field(max_length=500)]] = Field(max_length=10)
