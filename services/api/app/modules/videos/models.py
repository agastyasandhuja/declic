from __future__ import annotations

import hashlib
import json
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")]
Text = Annotated[str, Field(min_length=1, max_length=1000)]
Format = Literal["dialogue_gameplay", "visual_explainer", "space_explainer", "math_explainer"]


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
    input_values: list[int] = Field(default_factory=list, max_length=5)
    trace_kind: Literal["linked_list_reverse", "none"] = "linked_list_reverse"
    presentation: Literal["guided_v1", "reference_v2", "reference_v3"] = "reference_v3"
    format_id: Format
    teaching_approach: Identifier
    target_duration_seconds: int = Field(default=45, ge=20, le=60)
    scope: Literal["private", "shared_generic_candidate"] = "private"
    owner_user_id: Identifier | None = None
    template_version: str = "3.0.0"
    matrix_a: list[list[int]] = Field(default_factory=list, max_length=3)
    matrix_b: list[list[int]] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def consistent(self):
        if self.format_id != "math_explainer" and self.target_duration_seconds < 30:
            raise ValueError("Spoken lessons require at least 30 seconds")
        if self.format_id == "math_explainer":
            if self.trace_kind != "none" or self.presentation != "reference_v3":
                raise ValueError("Math template requires reference_v3 and trace_kind none")
            a, b = self.matrix_a, self.matrix_b
            if not a or not b or not 2 <= len(a) <= 3 or not 2 <= len(b) <= 3:
                raise ValueError("Provide two bounded matrices")
            if any(
                len(row) != len(m[0])
                or not 2 <= len(row) <= 3
                or any(isinstance(v, bool) or not -9 <= v <= 9 for v in row)
                for m in (a, b)
                for row in m
            ) or len(a[0]) != len(b):
                raise ValueError(
                    "Matrices must be rectangular, compatible and contain integers -9..9"
                )
        elif self.matrix_a or self.matrix_b:
            raise ValueError("Matrices require the math template")
        if self.trace_kind == "linked_list_reverse" and len(self.input_values) < 2:
            raise ValueError("Linked-list trace requires at least two nodes")
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


class TeachingBeat(Record):
    kind: Literal["hook", "prediction", "reveal", "retrieval", "feedback"]
    segment_id: Identifier
    text: Annotated[str, Field(min_length=1, max_length=72)]


class ImageRequest(Record):
    asset_id: Identifier
    query: Annotated[str, Field(min_length=3, max_length=120)]
    provider: Literal["nasa", "commons", "openverse"] = "commons"
    purpose: Annotated[str, Field(min_length=3, max_length=180)]
    fact_ids: list[Identifier] = Field(min_length=1, max_length=6)


class Shot(Record):
    shot_id: Identifier
    segment_id: Identifier
    kind: Literal["image", "diagram", "kinetic", "space"]
    diagram_demo: Literal["trace", "broken_first_link"] = Field(
        default="trace",
        description="For an opening misconception ONLY, broken_first_link shows "
        "the first link severed before saving; trace shows the real verified algorithm.",
    )
    asset_ids: list[Identifier] = Field(default_factory=list, max_length=2)
    headline: Annotated[str, Field(max_length=52)] = ""
    labels: list[Annotated[str, Field(min_length=1, max_length=24)]] = Field(
        default_factory=list, max_length=5
    )
    camera: Literal["push", "pull", "pan_left", "pan_right", "orbit", "drift"] = "push"
    layout: Literal["full", "insert", "split"] = "full"
    space_mode: Literal[
        "starfield",
        "galaxy",
        "cosmic_web",
        "cosmic_sheet",
        "cosmic_overview",
        "filament_detail",
        "solar_system",
        "nebula",
        "light_travel",
        "lookback",
        "scale_ladder",
        "gravity",
    ] = "galaxy"
    fact_ids: list[Identifier] = Field(min_length=1, max_length=6)


class ImageChoice(Record):
    asset_id: Identifier
    candidate_id: Identifier


class ImageSelection(Record):
    choices: list[ImageChoice] = Field(max_length=6)


class Storyboard(Record):
    schema_version: Literal["1"] = "1"
    title: Annotated[str, Field(min_length=1, max_length=90)]
    segments: list[Segment] = Field(min_length=3, max_length=16)
    events: list[Event] = Field(default_factory=list, max_length=20)
    # Optional for reading historical artifacts; mandatory for new generation.
    teaching_beats: list[TeachingBeat] = Field(default_factory=list, max_length=5)
    image_requests: list[ImageRequest] = Field(default_factory=list, max_length=6)
    shots: list[Shot] = Field(default_factory=list, max_length=16)

    def validate_for(self, brief: Brief, *, require_engagement=False):
        ids = [s.segment_id for s in self.segments]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate segment IDs")
        facts = {f.fact_id for f in brief.approved_facts}
        covered = {f for s in self.segments for f in s.fact_ids}
        if not set(brief.must_cover) <= covered or not covered <= facts:
            raise ValueError("Missing or invented fact coverage")
        roles = {s.speaker_role for s in self.segments}
        if brief.format_id != "dialogue_gameplay" and roles != {"narrator"}:
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
        if brief.trace_kind == "none":
            expected = []
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
        # Validate semantic cue order before buying narration. Matching substrings alone
        # allowed the same speech moment to drive different nodes out of order.
        cue_order = []
        for e in self.events:
            text = segments[e.cue.segment_id].spoken_text
            start, cursor = 0, 0
            for _ in range(e.cue.occurrence + 1):
                start = text.index(e.cue.phrase, cursor)
                cursor = start + len(e.cue.phrase)
            cue_order.append(
                (ids.index(e.cue.segment_id), cursor if e.cue.edge == "end" else start)
            )
        if any(a >= b for a, b in zip(cue_order, cue_order[1:], strict=False)):
            raise ValueError(
                "Every trace cue must occur strictly later in the script than the prior cue"
            )
        if (require_engagement and brief.presentation == "guided_v1") or self.teaching_beats:
            self.validate_engagement()
        if brief.presentation in {"reference_v2", "reference_v3"}:
            self.validate_shots(brief)
        return self

    def validate_shots(self, brief):
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(s.spoken_text for s in self.segments))
        for first, second in zip(sentences, sentences[1:], strict=False):
            if len(first.split()) >= 7 and first.casefold() == second.casefold():
                raise ValueError("Remove the immediately repeated narration sentence")
        if self.teaching_beats:
            raise ValueError(
                "Reference presentation uses continuous narration, not quiz-card beats"
            )
        if [s.segment_id for s in self.shots] != [s.segment_id for s in self.segments]:
            raise ValueError("Provide exactly one shot per narration segment, in spoken order")
        if len({s.shot_id for s in self.shots}) != len(self.shots):
            raise ValueError("Shot IDs must be unique")
        assets = {a.asset_id for a in self.image_requests}
        if len(assets) != len(self.image_requests):
            raise ValueError("Image request IDs must be unique")
        facts = {f.fact_id for f in brief.approved_facts}
        for item in [*self.shots, *self.image_requests]:
            if not set(item.fact_ids) <= facts:
                raise ValueError("Shot/image references an unapproved fact")
        for shot in self.shots:
            if not set(shot.asset_ids) <= assets:
                raise ValueError("Shot references an unknown image request")
            if shot.kind == "image" and not shot.asset_ids:
                raise ValueError("An image shot requires a requested image")
            if shot.kind == "space" and brief.format_id != "space_explainer":
                raise ValueError("Space scenes require the space format")
        if len(self.shots) < 6 or len({s.camera for s in self.shots}) < 2:
            raise ValueError("Reference videos need at least six shots and varied camera movement")
        if brief.format_id == "space_explainer":
            spatial = [s for s in self.shots if s.kind == "space"]
            if len(spatial) < 4 or len({s.space_mode for s in spatial}) < 2:
                raise ValueError(
                    "Space template requires at least four spatial shots and two space modes"
                )
            if len([a for a in self.image_requests if a.provider == "nasa"]) < 2:
                raise ValueError(
                    "Space template requires at least two relevant NASA image requests"
                )
        for shot in self.shots:
            if shot.diagram_demo != "trace":
                if brief.trace_kind != "linked_list_reverse" or shot.kind != "diagram":
                    raise ValueError("Mistake demonstration requires a linked-list diagram")
                save_segment = next(e.cue.segment_id for e in self.events if e.action == "save")
                positions = [s.segment_id for s in self.segments]
                if positions.index(shot.segment_id) >= positions.index(save_segment):
                    raise ValueError(
                        "Mistake demonstration is allowed only before the real trace saves"
                    )
        if brief.trace_kind == "linked_list_reverse":
            event_segments = {e.cue.segment_id for e in self.events}
            if any(s.kind != "diagram" for s in self.shots if s.segment_id in event_segments):
                raise ValueError(
                    "Show the trusted diagram throughout each segment containing trace events"
                )
        if any("dot next" in s.spoken_text.lower() for s in self.segments):
            raise ValueError("Use natural spoken language: say next pointer, never dot next")
        if len(self.segments[0].spoken_text.split()) > 14:
            raise ValueError("Open mid-thought with a concrete hook, at most fourteen words")
        if brief.presentation == "reference_v3":
            if brief.format_id == "visual_explainer" and brief.trace_kind == "none":
                used = [s.asset_ids[0] for s in self.shots if s.kind == "image"]
                if len(set(used)) < 4 or any(used.count(a) > 2 for a in used):
                    raise ValueError(
                        "Photo explainer needs at least four distinct scene-relevant images; "
                        "at most two uses each"
                    )
                if any(
                    a.kind == b.kind == "image" and set(a.asset_ids) & set(b.asset_ids)
                    for a, b in zip(self.shots, self.shots[1:], strict=False)
                ):
                    raise ValueError("Adjacent photo shots must not reuse an image")
            if brief.format_id == "space_explainer":
                spatial = [s for s in self.shots if s.kind == "space"]
                if len({s.space_mode for s in spatial}) < 4:
                    raise ValueError(
                        "Use four genuinely different spatial demonstrations, not camera changes"
                    )
                if any(
                    a.kind == b.kind == "space" and a.space_mode == b.space_mode
                    for a, b in zip(self.shots, self.shots[1:], strict=False)
                ):
                    raise ValueError("Adjacent space shots must demonstrate different scene types")
            if brief.format_id == "dialogue_gameplay":
                turns = sum(
                    a.speaker_role != b.speaker_role
                    for a, b in zip(self.segments, self.segments[1:], strict=False)
                )
                snarks = sum(
                    s.speaker_role == "stewie" and s.delivery == "sarcastic" for s in self.segments
                )
                if turns < 4 or snarks < 2:
                    raise ValueError(
                        "Use at least four speaker changes and two concise, concept-related "
                        "Stewie sarcastic replies"
                    )
        return self

    def validate_engagement(self):
        beats = self.teaching_beats
        if [b.kind for b in beats] != ["hook", "prediction", "reveal", "retrieval", "feedback"]:
            raise ValueError("Require hook, prediction, reveal, retrieval, feedback teaching beats")
        positions = {s.segment_id: i for i, s in enumerate(self.segments)}
        if any(b.segment_id not in positions for b in beats):
            raise ValueError("Unknown teaching beat segment")
        indexes = [positions[b.segment_id] for b in beats]
        if any(a >= b for a, b in zip(indexes, indexes[1:], strict=False)):
            raise ValueError("Teaching beats must reference distinct segments in spoken order")
        if indexes[:2] != [0, 1] or indexes[-2:] != [
            len(self.segments) - 2,
            len(self.segments) - 1,
        ]:
            raise ValueError("Open with hook and prediction; end with retrieval and feedback")
        hook_words = len(self.segments[0].spoken_text.split())
        prediction_words = len(self.segments[1].spoken_text.split())
        if hook_words > 8 or prediction_words > 14:
            raise ValueError(
                "Shorten BOTH opening segments: hook must be at most eight spoken words "
                f"(got {hook_words}); prediction at most fourteen (got {prediction_words}). "
                "Count space-separated words before resubmitting."
            )
        if any(len(b.text.split()) > 12 or not b.text.strip() for b in beats):
            raise ValueError("Teaching beat text must be short, nonblank phone-readable text")
        if any(not self.segments[indexes[i]].fact_ids for i in (2, 4)):
            raise ValueError("Reveal and retrieval feedback must reference approved facts")
        # The trace must finish before recall; do not display its answer while asking.
        if any(positions[e.cue.segment_id] >= indexes[-2] for e in self.events):
            raise ValueError("Finish the demonstration before retrieval")
        return self


class SceneSource(Record):
    source: Annotated[str, Field(min_length=30, max_length=40000)]


class ContentReview(Record):
    passed: bool
    issues: list[Annotated[str, Field(max_length=500)]] = Field(max_length=10)


class RenderReview(ContentReview):
    notes: list[Annotated[str, Field(max_length=600)]] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def blocking_only(self):
        if self.passed and self.issues:
            raise ValueError(
                "A passed review has issues=[]; place nonblocking observations in notes"
            )
        return self


class ImageFraming(Record):
    shot_id: Identifier
    asset_id: Identifier
    focus_x: float = Field(ge=0, le=1)
    focus_y: float = Field(ge=0, le=1)
    fit: Literal["cover", "contain"]
    zoom_start: float = Field(ge=1, le=1.35)
    zoom_end: float = Field(ge=1, le=1.35)


class ImageReview(ContentReview):
    framing: list[ImageFraming] = Field(max_length=32)
