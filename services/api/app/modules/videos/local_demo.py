"""Local operator-authored generic lessons. No model SDK or publication side effects."""

import argparse
import concurrent.futures
import json
import math
import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, model_validator

from .media import atomic_json, sha256
from .models import Fact, Identifier, Record, digest
from .narration.service import synthesize
from .narration.timing import alignment_words, caption_groups, vtt


class Node(Record):
    id: Identifier
    label: str = Field(max_length=24)
    value: str = Field(default="", max_length=16)
    x: float = Field(ge=0.05, le=0.95)
    y: float = Field(ge=0.05, le=0.95)
    to_x: float | None = Field(default=None, ge=0.05, le=0.95)
    to_y: float | None = Field(default=None, ge=0.05, le=0.95)
    glyph: Literal["circle", "box", "person", "book", "crate", "coin"] = "circle"


class Edge(Record):
    source: Identifier
    target: Identifier


class Scene(Record):
    kind: Literal["nodes", "tree", "matrix", "balance", "timeline", "inventory"]
    nodes: list[Node] = Field(default_factory=list, max_length=9)
    edges: list[Edge] = Field(default_factory=list, max_length=12)
    equation: str = Field(default="", max_length=60)
    matrix_a: list[list[int]] = Field(default_factory=list, max_length=3)
    matrix_b: list[list[int]] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def valid_graph(self):
        ids = {node.id for node in self.nodes}
        if len(ids) != len(self.nodes) or any(
            edge.source not in ids or edge.target not in ids or edge.source == edge.target
            for edge in self.edges
        ):
            raise ValueError("Edges require unique existing distinct nodes")
        a, b = self.matrix_a, self.matrix_b
        if bool(a) != bool(b):
            raise ValueError("Both matrices are required")
        if a and (
            self.kind != "matrix"
            or not 2 <= len(a) <= 3
            or not 2 <= len(b) <= 3
            or any(
                not 2 <= len(row) <= 3
                or len(row) != len(matrix[0])
                or any(type(v) is not int or abs(v) > 9 for v in row)
                for matrix in (a, b)
                for row in matrix
            )
            or len(a[0]) != len(b)
        ):
            raise ValueError("Matrices must be bounded rectangular compatible integer matrices")
        if not a and not self.nodes:
            raise ValueError("A scene needs actual nodes or matrices")
        return self


class Segment(Record):
    speaker_role: Literal["narrator", "peter", "stewie"]
    spoken_text: str = Field(min_length=1, max_length=450)
    fact_ids: list[Identifier] = Field(min_length=1, max_length=8)


class Quiz(Record):
    prompt: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3, strict=True)
    explanation: str = Field(min_length=1, max_length=1000)


class Lesson(Record):
    lesson_id: Identifier
    course_id: Literal["demo_cs210", "demo_acc233", "demo_his110", "demo_math235"]
    objective_id: Identifier
    title: str = Field(min_length=1, max_length=90)
    learning_goal: str = Field(min_length=1, max_length=500)
    format_style: Literal["dialogue", "graphic", "math", "cartoon", "three_d", "timeline"]
    approved_facts: list[Fact] = Field(min_length=2, max_length=12)
    segments: list[Segment] = Field(min_length=6, max_length=10)
    quizzes: list[Quiz] = Field(min_length=1, max_length=2)
    visual_plan: list[Scene] = Field(min_length=6, max_length=10)

    @model_validator(mode="after")
    def grounded(self):
        ids = {fact.fact_id for fact in self.approved_facts}
        if len(ids) != len(self.approved_facts) or any(
            not set(segment.fact_ids) <= ids for segment in self.segments
        ):
            raise ValueError("Every spoken segment must cite the supplied approved facts")
        if len(self.visual_plan) != len(self.segments):
            raise ValueError("Exactly one visual scene per spoken segment")
        if len(self.segments[0].spoken_text.split()) > 14:
            raise ValueError("Opening must be at most 14 words")
        if self.format_style == "dialogue":
            roles = [s.speaker_role for s in self.segments]
            if (
                set(roles) != {"peter", "stewie"}
                or sum(a != b for a, b in zip(roles, roles[1:], strict=False)) < 4
            ):
                raise ValueError("Dialogue requires both characters and four speaker changes")
        elif any(s.speaker_role != "narrator" for s in self.segments):
            raise ValueError("Non-dialogue lessons use a narrator")
        return self


class Batch(Record):
    schema_version: Literal["1"] = "1"
    lessons: list[Lesson] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({lesson.lesson_id for lesson in self.lessons}) != len(self.lessons):
            raise ValueError("Lesson IDs must be unique")
        return self


def prepare(lesson, output, assets_root, *, local_speech=False, narrator_voice=None):
    """No authoring API: only explicit narration, cached by frozen text and voice."""
    from .generation.providers import ElevenLabs

    folder = output / "pack" / lesson.lesson_id
    assets = folder / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    provider = None if local_speech else ElevenLabs()
    voices = {
        role: os.environ.get(f"ELEVENLABS_{role.upper()}_VOICE_ID", "")
        for role in ("peter", "stewie", "narrator")
    }
    if narrator_voice:
        voices["narrator"] = narrator_voice
    if local_speech:
        voices = {"peter": "Alex", "stewie": "Daniel", "narrator": "Daniel"}
    if any(not voices[s.speaker_role] for s in lesson.segments):
        raise ValueError("Missing configured voice; explicitly choose --local-speech if needed")
    brief = SimpleNamespace(
        installment_example=None,
        format_id="visual_explainer",
        presentation="local_authored",
        scope="shared_generic",
        owner_user_id=None,
    )
    segments, words, now = [], [], 0.0
    try:
        for index, segment in enumerate(lesson.segments):
            audio, meta = synthesize(
                segment,
                brief,
                provider,
                voices[segment.speaker_role],
                assets_root / ".local/video-audio-cache",
                fixture=local_speech,
            )
            name = f"speech-{index}.wav"
            shutil.copyfile(audio, assets / name)
            start = math.ceil(now * 30) / 30
            end = start + meta["duration"]
            words.extend(
                dict(word, segment_id=str(index))
                for word in alignment_words(
                    meta["alignment"], meta["duration"], start, segment.speaker_role
                )
            )
            segments.append(
                {
                    **segment.model_dump(),
                    "start": start,
                    "end": end,
                    "duration": meta["duration"],
                    "audio": name,
                    "voice_id": voices[segment.speaker_role],
                    "envelope": meta["envelope"],
                    "scene": lesson.visual_plan[index].model_dump(),
                }
            )
            now = end + 0.16
    finally:
        if provider:
            provider.client.close()
    duration = math.ceil((now + 0.3) * 30) / 30
    if not 30 <= duration <= 60:
        atomic_json(folder / "timing-repair.json", {"duration": duration, "segments": segments})
        raise ValueError(
            f"{lesson.lesson_id}: {duration:.2f}s; edit speech to 30–60s, audio cached"
        )
    if segments[0]["duration"] > 6:
        raise ValueError("Opening exceeds six seconds; shorten first segment")
    characters = {}
    if lesson.format_style == "dialogue":
        for role in ("peter", "stewie"):
            name = "stewie-standing-v2.png" if role == "stewie" else "peter.png"
            source = assets_root / ".local/video-assets" / name
            if not source.is_file():
                raise ValueError(f"Missing approved local {role} character asset")
            shutil.copyfile(source, assets / name)
            characters[role] = name
    data = {
        **lesson.model_dump(),
        "id": lesson.lesson_id,
        "frames": round(duration * 30),
        "duration": duration,
        "segments": segments,
        "words": words,
        "captions": caption_groups(words),
        "characters": characters,
        "narration_source": "macos_speech_estimated_alignment" if local_speech else "elevenlabs",
        "narration_model": getattr(provider, "model", "macos_say"),
        "authoring_source": "explicit_local_import",
        "review_status": "pending",
        "source_digest": digest(lesson.model_dump()),
    }
    atomic_json(folder / "lesson.json", data)
    (folder / "captions.vtt").write_text(vtt(data["captions"]))
    atomic_json(folder / "captions.json", data["captions"])
    atomic_json(
        folder / "manifest.json",
        {
            "schema_version": "1",
            "lesson_digest": digest(data),
            "files": {
                str(p.relative_to(folder)): sha256(p)
                for p in folder.rglob("*")
                if p.is_file() and p.name not in {"manifest.json", "timing-repair.json"}
            },
        },
    )
    return {"lesson_id": lesson.lesson_id, "duration": duration, "review_status": "pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["schema", "validate", "prepare"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assets-root", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--only", default="")
    parser.add_argument("--local-speech", action="store_true")
    parser.add_argument("--narrator-voice")
    parser.add_argument("--workers", type=int, choices=[1, 2, 3, 4], default=2)
    args = parser.parse_args()
    if args.command == "schema":
        atomic_json(args.output, Batch.model_json_schema())
        return
    batch = Batch.model_validate_json(args.input.read_text())
    if args.command == "validate":
        atomic_json(args.output, batch.model_dump())
        print(json.dumps({"validated": len(batch.lessons)}))
        return
    if not args.assets_root:
        parser.error("prepare requires --assets-root for explicitly configured cache/assets")
    if args.env_file:
        load_dotenv(args.env_file, override=False)
        load_dotenv(args.assets_root / "services/api/.env", override=False)
    wanted = (
        set(args.only.split(",")) if args.only else {lesson.lesson_id for lesson in batch.lessons}
    )
    if not wanted <= {lesson.lesson_id for lesson in batch.lessons}:
        parser.error("Unknown lesson ID")

    def one(lesson):
        return prepare(
            lesson,
            args.output,
            args.assets_root,
            local_speech=args.local_speech,
            narrator_voice=args.narrator_voice,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(one, lesson): lesson.lesson_id
            for lesson in batch.lessons
            if lesson.lesson_id in wanted
        }
        failures = []
        for future in concurrent.futures.as_completed(futures):
            try:
                print(json.dumps(future.result()), flush=True)
            except Exception as error:
                failures.append(futures[future])
                print(
                    json.dumps(
                        {
                            "lesson_id": futures[future],
                            "state": "preparation_failed",
                            "error": str(error)[:300],
                        }
                    ),
                    flush=True,
                )
        if failures:
            raise SystemExit(
                "Repair failed lesson IDs and retry with --only; completed packs remain"
            )


if __name__ == "__main__":
    main()
