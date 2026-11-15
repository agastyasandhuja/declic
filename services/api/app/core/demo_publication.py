"""Operator-only publication of explicitly reviewed authored generic demo renders.

This bridge consumes completed files. It cannot generate, approve, or promote
private Canvas content. The existing storage verifier and Atlas publication fence
remain responsible for byte integrity and atomic visibility.
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pymongo.errors import DuplicateKeyError

from app.core.demo_catalog import CATALOG_OWNER
from app.modules.videos.media import contained, sha256
from app.modules.videos.models import digest
from app.modules.videos.repository import new_job

POLICY = "agent_reviewed_generic_demo_v1"
FORMAT = {
    "dialogue": "dialogue_gameplay",
    "graphic": "visual_explainer",
    "math": "math_explainer",
    "cartoon": "analogy_story",
    "three_d": "space_explainer",
    "timeline": "visual_explainer",
}


RENDERERS = {"generic": "demo-library", "jensen_shop": "jensen-shop"}


def renderer_digest(root, profile="generic"):
    # Operator-selected, installed templates only. A lesson or review cannot
    # nominate arbitrary code or substitute its own expected source hash.
    if profile not in RENDERERS:
        raise ValueError("Unknown installed demo renderer")
    source = root / "services/renderer/experiments" / RENDERERS[profile]
    paths = [
        *sorted((source / "src").glob("*")),
        source / "render.mjs",
        root / "services/renderer/src/PopCaptions.tsx",
        root / "services/renderer/experiments/voxel-story/src/ModelKit.ts",
    ]
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


def publication_sources(lessons, root, work, overrides=None):
    """Resolve operator overrides while preserving each renderer's provenance."""
    overrides = {} if overrides is None else overrides
    identifiers = {lesson.lesson_id for lesson in lessons}
    if not isinstance(overrides, dict) or set(overrides) - identifiers:
        raise ValueError("Renderer overrides must name lessons in this batch")
    sources = {}
    for identifier in identifiers:
        entry = overrides.get(identifier, {})
        if not isinstance(entry, dict) or set(entry) - {"renderer", "work"}:
            raise ValueError("Renderer override accepts only renderer and work")
        profile = entry.get("renderer", "generic")
        if not isinstance(profile, str) or profile not in RENDERERS:
            raise ValueError("Unknown installed demo renderer")
        selected_work = work
        if "work" in entry:
            if not isinstance(entry["work"], str) or not Path(entry["work"]).is_absolute():
                raise ValueError("Renderer work override must be an absolute local path")
            selected_work = Path(entry["work"])
        sources[identifier] = (selected_work.resolve(), renderer_digest(root, profile))
    return sources


def validate_review(lesson, work, review, expected_renderer):
    """Return validated immutable file references; never supply approval defaults."""
    source = lesson.model_dump(mode="json")
    identifier = lesson.lesson_id
    # Local authored IDs resolve only under the explicitly selected root.
    if not identifier.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Invalid authored lesson directory")
    pack = contained(work, f"pack/{identifier}")
    output = contained(work, f"output/{identifier}")
    data = json.loads(contained(pack, "lesson.json").read_text())
    manifest = json.loads(contained(pack, "manifest.json").read_text())
    source_hash = digest(source)
    if (
        not lesson.objective_id.startswith("demo_")
        or len(lesson.quizzes) != 2
        or data.get("source_digest") != source_hash
        or data.get("authoring_source") != "explicit_local_import"
        or data.get("narration_source") not in {"elevenlabs", "macos_speech_estimated_alignment"}
        or manifest.get("lesson_digest") != digest(data)
    ):
        raise ValueError("Rendered pack does not match the reviewed generic source")
    if any(data.get(key) != value for key, value in source.items() if key != "segments"):
        raise ValueError("Prepared teaching content differs from reviewed source")
    if "segments" in source:
        rendered_segments = data.get("segments", [])
        if len(rendered_segments) != len(source["segments"]):
            raise ValueError("Prepared narration differs from reviewed source")
        for index, segment in enumerate(source["segments"]):
            if (
                any(rendered_segments[index].get(key) != value for key, value in segment.items())
                or rendered_segments[index].get("scene") != source["visual_plan"][index]
            ):
                raise ValueError("Prepared narration/scene differs from reviewed source")
    files = manifest.get("files", {})
    expected_files = {
        str(p.relative_to(pack))
        for p in pack.rglob("*")
        if p.is_file() and p.name not in {"manifest.json", "timing-repair.json"}
    }
    if set(files) != expected_files or not {"lesson.json", "captions.json", "captions.vtt"} <= set(
        files
    ):
        raise ValueError("Pack manifest must cover every published input")
    for relative, expected in files.items():
        if sha256(contained(pack, relative)) != expected:
            raise ValueError("A prepared artifact changed")
    for kind in ("stills", "video"):
        provenance = json.loads(contained(output, f"{kind}-provenance.json").read_text())
        if (
            provenance.get("lesson_sha256") != sha256(pack / "lesson.json")
            or provenance.get("pack_sha256") != sha256(pack / "manifest.json")
            or provenance.get("renderer_source") != expected_renderer
        ):
            raise ValueError("Stills/video do not match the exact pack and renderer")
    assets = {
        "video": contained(output, "lesson.mp4"),
        "thumbnail": contained(output, "frame-01.png"),
        "captions": contained(pack, "captions.vtt"),
        "words": contained(pack, "captions.json"),
        "quality": contained(output, "quality.json"),
    }
    hashes = {name: sha256(path) for name, path in assets.items()}
    quality = json.loads(assets["quality"].read_text())
    if (
        quality.get("media_checks") != "passed"
        or quality.get("sha256") != hashes["video"]
        or not 30 <= quality.get("duration_seconds", 0) <= 60
        or assets["video"].stat().st_size > 45 * 1024 * 1024
    ):
        raise ValueError("Final video has not passed the demo delivery checks")
    frames = json.loads(contained(output, "frame-index.json").read_text())
    if not isinstance(frames, list) or len(frames) != len(lesson.segments) * 3:
        raise ValueError("Review beginning/action/end frames for every spoken scene")
    frame_hashes = {frame["file"]: sha256(contained(output, frame["file"])) for frame in frames}
    if len(frame_hashes) != len(frames):
        raise ValueError("Duplicate review frame")
    if (
        review.get("reviewer") != "codex"
        or review.get("policy") != POLICY
        or review.get("content_digest") != source_hash
        or review.get("renderer_source_digest") != expected_renderer
        or review.get("video_sha256") != hashes["video"]
        or review.get("artifacts") != hashes
        or review.get("frames") != frame_hashes
        or review.get("quiz_status") != "passed"
        or any(
            review.get(key) is not True
            for key in (
                "checked_facts",
                "content",
                "visuals",
                "audio_sync",
                "assets",
                "generic_lineage",
            )
        )
    ):
        raise ValueError(
            "Explicit Codex review must bind content, quizzes, media, and all scene frames"
        )
    return data, assets, quality, hashes


def publish_lesson(repository, storage, lesson, work, review, expected_renderer):
    data, files, quality, hashes = validate_review(lesson, work, review, expected_renderer)
    recipe = {
        "pipeline": "authored_generic_demo_v1",
        "renderer_source": expected_renderer,
        "content_digest": digest(lesson.model_dump(mode="json")),
        "artifacts": hashes,
    }
    key = "demo_" + digest(recipe)
    ready = repository.ready(key, CATALOG_OWNER)
    if ready:
        if ready.get("scope") != "shared_generic" or ready.get("owner_user_id") is not None:
            raise ValueError("Generation key has conflicting ownership")
        return ready
    job = new_job(
        key,
        CATALOG_OWNER,
        {"scope": "shared_generic_candidate", "lesson": lesson.model_dump(mode="json")},
        recipe,
    )
    job.update(state="awaiting_review", stage="reviewed", attempt=2, video_sha256=hashes["video"])
    try:
        repository.jobs.insert_one(job.copy())
    except DuplicateKeyError:
        job = repository.jobs.find_one({"generation_key": key, "owner_user_id": CATALOG_OWNER})
        if not job:
            raise ValueError("Generic publication job has conflicting ownership") from None
    claimed = repository.claim_review(job["job_id"], CATALOG_OWNER, hashes["video"])
    if not claimed:
        ready = repository.ready(key, CATALOG_OWNER)
        if ready:
            return ready
        raise ValueError("Reviewed publication is already in progress; retry after its lease")
    try:
        storage.verify_private_bucket()
        assets = {}
        for name, path in files.items():
            # Content-addressed keys contain no person, course, or source names.
            object_key = f"{claimed['job_id']}/{hashes[name]}{path.suffix}"
            assets[name] = storage.put(object_key, path)
        # Revalidate files immediately before visibility. A prior approved review
        # is never approval for changed files or newly generated output.
        validate_review(lesson, work, review, expected_renderer)
        now = datetime.now(UTC).isoformat()
        variant = {
            "schema_version": "1",
            "video_id": uuid4().hex,
            "generation_key": key,
            "objective_id": lesson.objective_id,
            "lesson_request_id": lesson.lesson_id,
            "format_id": FORMAT[lesson.format_style],
            "teaching_approach": "authored_" + lesson.format_style,
            "level": "intro",
            "language": "en",
            "notation": "general",
            "scope": "shared_generic",
            "owner_user_id": None,
            "status": "ready",
            "title": lesson.title,
            "learning_goal": lesson.learning_goal,
            "duration_seconds": quality["duration_seconds"],
            "asset_id": hashes["video"],
            "assets": assets,
            "template_version": "authored_demo_v1",
            "brief_hash": recipe["content_digest"],
            "generation_version": "1.0.0",
            "quality_checks": {
                **quality,
                "publication_policy": POLICY,
                "human_review": "not_performed",
                "agent_review": "approved",
                "reviewer": "codex",
                "review_digest": digest(review),
                "narration_source": data["narration_source"],
            },
            "created_at": now,
            "ready_at": now,
        }
        repository.publish(claimed["job_id"], claimed["fence"], variant)
        return variant
    except Exception:
        # A storage retry must reuse these exact reviewed artifacts, never enter
        # the generation worker's queued/retry_wait states.
        repository.update(
            claimed["job_id"], claimed["fence"], {"state": "awaiting_review", "stage": "reviewed"}
        )
        raise


def main():
    from app.full_runtime import components
    from app.modules.videos.local_demo import Batch

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument(
        "--reviews", type=Path, required=True, help="Object mapping lesson IDs to explicit reviews"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Write resulting generic catalog manifest"
    )
    parser.add_argument(
        "--renderer-overrides",
        type=Path,
        help="Optional lesson-ID map of installed renderer and absolute work directory",
    )
    parser.add_argument("--apply", action="store_true", required=True)
    args = parser.parse_args()
    batch = Batch.model_validate_json(args.input.read_text())
    reviews = json.loads(args.reviews.read_text())
    sources = publication_sources(
        batch.lessons,
        Path(__file__).resolve().parents[4],
        args.work,
        json.loads(args.renderer_overrides.read_text()) if args.renderer_overrides else None,
    )
    # Validate the entire batch before the first remote write.
    for lesson in batch.lessons:
        work, expected_renderer = sources[lesson.lesson_id]
        validate_review(lesson, work, reviews.get(lesson.lesson_id, {}), expected_renderer)
    database, _, _, videos, _ = components()
    try:
        entries = []
        for lesson in batch.lessons:
            work, expected_renderer = sources[lesson.lesson_id]
            variant = publish_lesson(
                videos.repository,
                videos.storage,
                lesson,
                work,
                reviews[lesson.lesson_id],
                expected_renderer,
            )
            quizzes = [
                {
                    "quiz_id": f"{lesson.objective_id}_{lesson.lesson_id}_quiz_{i + 1}",
                    "revision": 1,
                    "objective_ids": [lesson.objective_id],
                    "prompt": quiz.prompt,
                    "options": [
                        {"option_id": str(j), "text": value} for j, value in enumerate(quiz.options)
                    ],
                    "correct_option_id": str(quiz.correct_index),
                    "explanation": quiz.explanation,
                    "scope": "shared_generic",
                    "owner_user_id": None,
                    "source_refs": [],
                }
                for i, quiz in enumerate(lesson.quizzes)
            ]
            entries.append(
                {
                    "objective_id": lesson.objective_id,
                    "video_id": variant["video_id"],
                    "quizzes": quizzes,
                }
            )
            print(json.dumps({"lesson_id": lesson.lesson_id, "published": True}), flush=True)
        manifest = {
            "schema_version": "1",
            "catalog_id": "shared_demo_v1",
            "revision": 1,
            "courses": [
                {"course_id": key, "title": title}
                for key, title in (
                    ("demo_cs210", "CS210 — Data Structures"),
                    ("demo_acc233", "ACC233 — Accounting"),
                    ("demo_his110", "HIS110 — History before 1500"),
                    ("demo_math235", "MATH235 — Linear Algebra"),
                )
            ],
            "objectives": list(
                {
                    lesson.objective_id: {
                        "objective_id": lesson.objective_id,
                        "course_id": lesson.course_id,
                        "title": lesson.title,
                        "level": "intro",
                        "language": "en",
                        "notation": "general",
                    }
                    for lesson in batch.lessons
                }.values()
            ),
            "lessons": entries,
        }
        from app.core.demo_catalog import DemoManifest

        args.output.write_text(DemoManifest.model_validate(manifest).model_dump_json(indent=2))
    finally:
        database.close()


if __name__ == "__main__":
    main()
