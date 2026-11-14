"""Synthetic publication boundary tests; these do not claim media quality."""

import json
from types import SimpleNamespace

import pytest

from app.modules.videos.media import sha256
from app.modules.videos.models import Brief, digest
from app.modules.videos.pipeline import ROOT, artifact_digests, generation_recipe
from app.modules.videos.publication import publish_private_demo
from app.modules.videos.repository import LocalVideoRepository, StaleLease


@pytest.fixture
def staged(tmp_path):
    repository = LocalVideoRepository(tmp_path / "jobs.db")
    brief = Brief.model_validate_json(
        (ROOT / "fixtures/learning/linked-list-brief.json").read_text()
    )
    brief = brief.model_copy(update={"scope": "private", "owner_user_id": "alice"})
    recipe = generation_recipe()
    row = repository.enqueue(brief.generation_key(recipe), "alice", brief.model_dump(), recipe)
    job = repository.claim()
    assert job["job_id"] == row["job_id"]
    work = tmp_path / "assets"
    for name in (
        "output/lesson.mp4",
        "captions.vtt",
        "captions.json",
        "output/frame-01.png",
        "output/quality.json",
    ):
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic test bytes, not a playable asset")
    board, lesson = {"synthetic": "storyboard"}, {"synthetic": "lesson"}
    (work / "pack").mkdir()
    for name, value in {
        "storyboard.json": board,
        "pack/lesson.json": lesson,
        "content-review.json": {"passed": True, "issues": [], "storyboard_digest": digest(board)},
        "render-review.json": {
            "passed": True,
            "issues": [],
            "lesson_digest": digest(lesson),
            "renderer_source": recipe["renderer_source"],
        },
    }.items():
        (work / name).write_text(json.dumps(value))
    hashes = artifact_digests(work)
    manifest = {
        "fixture": False,
        "recipe": recipe,
        "generation_key": brief.generation_key(recipe),
        "artifact_digests": hashes,
        "quality": {
            "media_checks": "passed",
            "sha256": hashes["output/lesson.mp4"],
            "duration_seconds": 45,
        },
    }
    uploads = []

    def put(key, path):
        uploads.append(key)
        return {"key": key, "sha256": sha256(path), "size": path.stat().st_size}

    storage = SimpleNamespace(verify_private_bucket=lambda: None, put=put)
    return repository, storage, job, brief, work, manifest, uploads


def test_automated_review_publishes_only_owned_variant_and_never_claims_human_approval(staged):
    repo, storage, job, brief, work, manifest, uploads = staged
    variant = publish_private_demo(repo, storage, job, brief, work, manifest)
    assert repo.video(variant["video_id"], "alice") is not None
    assert repo.video(variant["video_id"], "bob") is None
    assert repo.get(job["job_id"], "alice")["state"] == "succeeded"
    assert variant["quality_checks"]["human_review"] == "pending"
    assert len(uploads) == 5


@pytest.mark.parametrize("modified", ["storyboard.json", "pack/lesson.json", "captions.vtt"])
def test_changed_review_inputs_or_published_sidecars_do_not_upload(staged, modified):
    repo, storage, job, brief, work, manifest, uploads = staged
    (work / modified).write_text(json.dumps({"changed": True}))
    with pytest.raises(ValueError):
        publish_private_demo(repo, storage, job, brief, work, manifest)
    assert not uploads
    assert repo.ready(brief.generation_key(job["recipe"]), "alice") is None


def test_cancel_during_upload_prevents_readiness(staged):
    repo, storage, job, brief, work, manifest, uploads = staged
    original = storage.put

    def cancel_then_put(key, path):
        repo.cancel(job["job_id"], "alice")
        return original(key, path)

    storage.put = cancel_then_put
    with pytest.raises(StaleLease):
        publish_private_demo(repo, storage, job, brief, work, manifest)
    assert repo.ready(brief.generation_key(job["recipe"]), "alice") is None
    assert repo.get(job["job_id"], "alice")["state"] == "cancelled"
