"""Synthetic artifact tests; these never assert the dummy media is actually playable."""

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.core.demo_publication import POLICY, publish_lesson, validate_review
from app.modules.videos.media import sha256
from app.modules.videos.models import digest
from app.modules.videos.repository import AtlasVideoRepository


def reviewed_files(tmp_path):
    source = {
        "lesson_id": "demo_lesson",
        "objective_id": "demo_objective",
        "course_id": "demo_cs210",
    }
    lesson = SimpleNamespace(
        **source,
        segments=[{}] * 6,
        quizzes=[{}, {}],
        format_style="graphic",
        title="Generic synthetic lesson",
        learning_goal="Understand generic material",
        model_dump=lambda **kwargs: deepcopy(source),
    )
    pack = tmp_path / "pack/demo_lesson"
    pack.mkdir(parents=True)
    output = tmp_path / "output/demo_lesson"
    output.mkdir(parents=True)
    data = {
        **source,
        "source_digest": digest(source),
        "authoring_source": "explicit_local_import",
        "narration_source": "macos_speech_estimated_alignment",
    }
    (pack / "lesson.json").write_text(json.dumps(data))
    (pack / "captions.json").write_text("[]")
    (pack / "captions.vtt").write_text("WEBVTT\n")
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "lesson_digest": digest(data),
                "files": {file.name: sha256(file) for file in pack.iterdir() if file.is_file()},
            }
        )
    )
    (output / "lesson.mp4").write_bytes(b"synthetic dummy bytes, no playback claim")
    quality = {
        "sha256": sha256(output / "lesson.mp4"),
        "media_checks": "passed",
        "duration_seconds": 40,
    }
    (output / "quality.json").write_text(json.dumps(quality))
    frames = []
    for i in range(18):
        name = f"frame-{i:02}.png"
        (output / name).write_bytes(b"synthetic frame " + str(i).encode())
        frames.append({"file": name, "frame": i * 30, "time": i})
    (output / "frame-index.json").write_text(json.dumps(frames))
    renderer = "a" * 64
    for kind in ("stills", "video"):
        (output / f"{kind}-provenance.json").write_text(
            json.dumps(
                {
                    "lesson_sha256": sha256(pack / "lesson.json"),
                    "pack_sha256": sha256(pack / "manifest.json"),
                    "renderer_source": renderer,
                }
            )
        )
    files = {
        "video": output / "lesson.mp4",
        "thumbnail": output / "frame-01.png",
        "quality": output / "quality.json",
        "captions": pack / "captions.vtt",
        "words": pack / "captions.json",
    }
    review = {
        "reviewer": "codex",
        "policy": POLICY,
        "content_digest": digest(source),
        "renderer_source_digest": renderer,
        "video_sha256": quality["sha256"],
        "artifacts": {name: sha256(file) for name, file in files.items()},
        "frames": {frame["file"]: sha256(output / frame["file"]) for frame in frames},
        "quiz_status": "passed",
        **dict.fromkeys(
            ("checked_facts", "content", "visuals", "audio_sync", "assets", "generic_lineage"), True
        ),
    }
    return lesson, review, renderer


def test_explicit_review_binds_source_renderer_assets_and_every_frame(tmp_path):
    lesson, review, renderer = reviewed_files(tmp_path)
    validate_review(lesson, tmp_path, review, renderer)
    for changes in (
        {"reviewer": "human"},
        {"generic_lineage": False},
        {"content_digest": "changed"},
        {"frames": {}},
        {"quiz_status": "pending"},
        {"renderer_source_digest": "changed"},
    ):
        with pytest.raises(ValueError):
            validate_review(lesson, tmp_path, {**review, **changes}, renderer)
    (tmp_path / "pack/demo_lesson/captions.vtt").write_text("changed")
    with pytest.raises(ValueError):
        validate_review(lesson, tmp_path, review, renderer)


def test_publication_uses_existing_fence_and_retries_without_generation(database, tmp_path):
    if database.mongo is None:
        pytest.skip("Requires isolated API_TEST_MONGODB_URI")
    lesson, review, renderer = reviewed_files(tmp_path)
    repository = AtlasVideoRepository(database.mongo)
    repository.initialize()
    calls = []
    fail = [True]

    def put(key, file):
        calls.append(key)
        if fail[0]:
            fail[0] = False
            raise RuntimeError("synthetic storage failure")
        return {"key": key, "sha256": sha256(file), "size": file.stat().st_size}

    storage = SimpleNamespace(verify_private_bucket=lambda: None, put=put)
    with pytest.raises(RuntimeError):
        publish_lesson(repository, storage, lesson, tmp_path, review, renderer)
    assert repository.catalog.count_documents({}) == 0
    job = repository.jobs.find_one({})
    assert job["state"] == "awaiting_review" and job["attempt"] == 2
    assert repository.claim() is None  # It must never enter the model/generation worker.
    result = publish_lesson(repository, storage, lesson, tmp_path, review, renderer)
    assert result["scope"] == "shared_generic" and result["owner_user_id"] is None
    assert result["quality_checks"]["human_review"] == "not_performed"
    assert result["quality_checks"]["publication_policy"] == POLICY
    prior = len(calls)
    again = publish_lesson(repository, storage, lesson, tmp_path, review, renderer)
    assert again["video_id"] == result["video_id"] and len(calls) == prior
    assert repository.catalog.count_documents({}) == 1
    assert repository.outbox.count_documents({}) == 1
