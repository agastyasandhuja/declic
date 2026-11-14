"""Music-led mathematical motion: trusted code computes every value and geometric plan."""

import json
import shutil
from pathlib import Path
from typing import Literal

from pydantic import Field

from .generation.providers import SYSTEM, Claude, ProviderError
from .media import atomic_json, sha256
from .models import Record, digest
from .music import CATALOG, stage_music
from .rendering import render


class MathDirection(Record):
    hook: str = Field(min_length=1, max_length=52)
    payoff: str = Field(min_length=1, max_length=64)
    music_id: Literal["cylinder_six", "cylinder_four"]
    rationale: str = Field(min_length=1, max_length=600)


def matrix_plan(a, b):
    """Derive row/column products and exact sums. Never trust model-provided arithmetic."""
    if not a or not b or len(a[0]) != len(b):
        raise ValueError("Incompatible matrices")
    seconds = 4.5 if len(a[0]) == 2 else 5
    cells = []
    for row in range(len(a)):
        for col in range(len(b[0])):
            products = [value * b[k][col] for k, value in enumerate(a[row])]
            start = 1.5 + len(cells) * seconds
            cells.append(
                {
                    "row": row,
                    "col": col,
                    "products": products,
                    "result": sum(products),
                    "start": start,
                    "end": start + seconds,
                }
            )
    return {"a": a, "b": b, "cells": cells}, cells[-1]["end"] + 1.5


def pythagorean_plan(sides):
    """Four congruent right triangles leave the same area in two arrangements."""
    if (
        not isinstance(sides, list)
        or len(sides) != 2
        or any(type(v) is not int or not 1 <= v <= 9 for v in sides)
    ):
        raise ValueError("Pythagorean sides must be two positive integers from 1 to 9")
    a, b = sides
    stages = [
        ("triangle", 0, 3),
        ("assemble", 3, 6),
        ("c_square", 6, 9),
        ("rearrange", 9, 14),
        ("area_sum", 14, 18),
        ("identity", 18, 22),
    ]
    return {
        "kind": "pythagorean_rearrangement",
        "a": a,
        "b": b,
        "c_squared": a * a + b * b,
        "outer_side": a + b,
        "triangle_area": a * b / 2,
        "areas": {"a_squared": a * a, "b_squared": b * b},
        "stages": [{"kind": kind, "start": start, "end": end} for kind, start, end in stages],
    }, 22


def generate_math(
    brief,
    work: Path,
    *,
    fixture=False,
    preview=False,
    render_video=True,
    stage=lambda _: None,
    check_cancelled=lambda: None,
):
    from .pipeline import artifact_digests, generation_recipe

    brief = type(brief).model_validate(brief.model_dump())
    work.mkdir(parents=True, exist_ok=True)
    pack = work / "pack"
    assets = pack / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    geometry = brief.math_topic == "pythagorean_rearrangement"
    math, duration = (
        pythagorean_plan(brief.pythagorean_sides)
        if geometry
        else matrix_plan(brief.matrix_a, brief.matrix_b)
    )
    recipe = generation_recipe(fixture=fixture)
    key = brief.generation_key(recipe)
    atomic_json(
        work / "request.json",
        {"brief": brief.model_dump(), "recipe": recipe, "generation_key": key},
    )
    stage("planning_math")
    turns = 0

    def charge():
        nonlocal turns
        check_cancelled()
        turns += 1
        if turns > 8:
            raise ProviderError("AGENT_BUDGET_EXHAUSTED")

    claude = None if fixture else Claude(charge=charge, cache_dir=work / "model-cache")
    direction_key = digest([brief.teaching_payload(), recipe["claude"], "math-direction-3"])
    cached = work / "math-direction.json"
    if cached.exists() and json.loads(cached.read_text()).get("key") == direction_key:
        direction = MathDirection.model_validate(json.loads(cached.read_text())["direction"])
    elif fixture:
        direction = MathDirection(
            hook="Why do the two square areas equal the third?"
            if geometry
            else "One row. One column. One answer.",
            payoff="Same square. Same triangles. Same remaining area."
            if geometry
            else "Each row meets each column.",
            music_id="cylinder_six",
            rationale="Synthetic direction fixture",
        )
    else:
        direction = claude.structured(
            MathDirection,
            SYSTEM
            + (
                "Direct a minimal music-led Pythagorean rearrangement proof. Four congruent right "
                "triangles tile the same outer square in two ways: first leaving a tilted square "
                "of area c squared, then two squares of areas a squared and b squared. The same "
                "triangles only translate, preserving shape and area. Never call an intermediate "
                "overlapping arrangement a proof. Only the two exact endpoint tilings establish "
                "the identity. No written explanation; large geometry, symbolic labels and one "
                "equation explain the concept. Hook/payoff are internal intent only. Choose a "
                "licensed instrumental catalog ID. No voice, prose, credit footer, or URLs. "
                "Never supply arithmetic or coordinates; trusted code supplies them."
                if geometry
                else "Direct a minimal, music-led matrix-multiplication short. No instructional "
                "captions or credit text on the canvas; oversized matrices and moving numbers "
                "do the teaching. "
                "Hook and payoff are internal editorial intent, not rendered text. "
                "Black canvas, serif math, "
                "purple rows and gold columns. Source matrices stay still; factors move into "
                "dot products and results slide into their cells. Choose a concise specific hook "
                "and useful final rule from the approved facts. No narration, financial claim, "
                "unrelated slogan or text requiring an unseen diagram. The hook should invite "
                "the viewer to follow the first dot product, e.g. 'How does this become 20?' "
                "only when 20 is the computed first result. Choose one licensed instrumental track "
                "ID from the catalog. Never output arithmetic: code supplies exact results."
            ),
            {"brief": brief.teaching_payload(), "computed_math": math, "music_catalog": CATALOG},
        )
    atomic_json(cached, {"key": direction_key, "direction": direction.model_dump()})
    check_cancelled()
    stage("sourcing_music")
    music = stage_music(direction.music_id, assets, duration, fixture=fixture)
    (work / "CREDITS.txt").write_text(
        f"{music.get('title')} — {music.get('creator', 'Local fixture')}\n"
        "Album: Cylinders\nLicensed under Creative Commons Attribution 4.0\n"
        "https://creativecommons.org/licenses/by/4.0/\nhttps://chriszabriskie.com/cylinders/\n"
        "Modifications: excerpt, fades and loudness normalization.\n"
        "Include this credit in the description when sharing the video.\n"
    )
    review_frames = [0, 30]
    for cell in math["stages"] if geometry else math["cells"]:
        review_frames.extend(
            round((cell["start"] + n * (cell["end"] - cell["start"])) * 30)
            for n in (0.34, 0.62, 0.80, 0.95)
        )
    lesson = {
        "schema_version": "1",
        "format_id": "math_explainer",
        "presentation": "reference_v3",
        "frame_count": round(duration * 30),
        "title": brief.title,
        "math": math,
        "hook": direction.hook,
        "payoff": direction.payoff,
        "audio_file": "soundtrack.wav",
        "audio_mode": "music",
        "music_credit": music,
        "minimal_math": True,
        "review_frames": review_frames,
        "events": [],
        "segments": [],
        "shots": [],
        "images": {},
        "captions": [],
        "teaching_beats": [],
        "characters": {},
        "trace_kind": "none",
        "custom_scene": False,
    }
    atomic_json(pack / "lesson.json", lesson)
    (work / "captions.vtt").write_text("WEBVTT\n\n")
    atomic_json(work / "captions.json", [])
    atomic_json(
        pack / "manifest.json",
        {
            "schema_version": "1",
            "files": [
                {"path": str(p.relative_to(pack)), "sha256": sha256(p), "size": p.stat().st_size}
                for p in pack.rglob("*")
                if p.is_file() and p.name != "manifest.json"
            ],
        },
    )
    if render_video and not fixture:
        stage("reviewing_rendered_math")
        render(
            pack, work / "preview-frames", True, check_cancelled=check_cancelled, stills_only=True
        )
        review = claude.review_render(brief, lesson, work / "preview-frames")
        atomic_json(
            work / "render-review.json",
            {
                **review.model_dump(),
                "lesson_digest": digest(lesson),
                "renderer_source": recipe["renderer_source"],
                "model": claude.model,
                "scope": "sampled_frames",
            },
        )
        atomic_json(work / "provider-usage.json", claude.usage)
        if not review.passed or review.issues:
            raise ProviderError("RENDER_REVIEW_REQUIRED")
    stage("rendering")
    report = (
        render(pack, work / "output", preview, check_cancelled=check_cancelled)
        if render_video
        else {"media_checks": "not_run"}
    )
    if render_video:
        # A standalone export must retain the licensed soundtrack's attribution.
        shutil.copyfile(work / "CREDITS.txt", work / "output" / "CREDITS.txt")
    motion_inspection = None
    if render_video:
        from .motion_review import stage_motion_review

        stage("staging_motion_inspection")
        motion_inspection = stage_motion_review(work, lesson)
    manifest = {
        "schema_version": "1",
        "generation_key": key,
        "recipe": recipe,
        "scope": brief.scope,
        "owner_user_id": brief.owner_user_id,
        "status": "validating",
        "quality": report,
        "motion_inspection": motion_inspection,
        "fixture": fixture,
        "custom_scene": False,
        "human_review": "pending",
        "storyboard_digest": digest(direction.model_dump()),
        "image_credits": {},
        "music_credit": music,
        "provider_usage": getattr(claude, "usage", []),
        "teaching_checks": {
            "policy": "pythagorean-area-motion-1" if geometry else "matrix-motion-1",
            "arithmetic": "computed_and_renderer_verified",
            "engagement_uplift": "unmeasured",
            "learning_uplift": "unmeasured",
        },
        "artifact_digests": {
            **artifact_digests(work),
            "output/CREDITS.txt": sha256(work / "output" / "CREDITS.txt"),
        }
        if render_video
        else {},
    }
    atomic_json(work / "generation-manifest.json", manifest)
    return manifest
