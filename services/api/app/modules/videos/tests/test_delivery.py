import hashlib

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.core.identity import Principal
from app.modules.videos.generation.providers import ProviderError
from app.modules.videos.media import sha256
from app.modules.videos.models import Brief
from app.modules.videos.pipeline import ROOT, artifact_digests
from app.modules.videos.publication import SupabaseVideoStorage, publish_validated_variant
from app.modules.videos.router import create_router
from app.modules.videos.service import VideoService


def test_storage_verifies_ambiguous_upload_and_rejects_wrong_bytes(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "https://storage.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic")
    file = tmp_path / "clip.mp4"
    file.write_bytes(b"synthetic video")
    key = "a" * 32 + "/" + sha256(file) + ".mp4"
    returned = file.read_bytes()

    def respond(request):
        if request.method == "POST":
            return httpx.Response(409, json={"code": "ResourceAlreadyExists"})
        return httpx.Response(200, content=returned)

    storage = SupabaseVideoStorage(httpx.Client(transport=httpx.MockTransport(respond)))
    assert storage.put(key, file)["sha256"] == hashlib.sha256(returned).hexdigest()
    returned = b"changed"
    with pytest.raises(ProviderError, match="DIGEST_MISMATCH"):
        storage.put(key, file)


def test_changed_sidecar_cannot_publish(tmp_path):
    brief = Brief.model_validate_json(
        (ROOT / "fixtures/learning/linked-list-brief.json").read_text()
    )
    for name in (
        "output/lesson.mp4",
        "captions.vtt",
        "captions.json",
        "output/frame-01.png",
        "output/quality.json",
    ):
        p = tmp_path / name
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(b"synthetic")
    hashes = artifact_digests(tmp_path)
    manifest = {
        "fixture": False,
        "recipe": {},
        "generation_key": brief.generation_key({}),
        "quality": {"media_checks": "passed", "sha256": hashes["output/lesson.mp4"]},
        "artifact_digests": hashes,
    }
    review = {
        "video_sha256": hashes["output/lesson.mp4"],
        "artifact_digests": hashes,
        **dict.fromkeys(("content", "visuals", "audio_sync", "assets"), True),
    }
    (tmp_path / "captions.vtt").write_text("changed")
    with pytest.raises(ValueError, match="every published artifact"):
        publish_validated_variant(None, None, {"recipe": {}}, brief, tmp_path, manifest, review)


def test_routes_never_sign_another_users_video():
    class Repo:
        def video(self, video_id, owner):
            assert owner == "bob"
            return None

    class Storage:
        def signed_url(self, key):
            pytest.fail("Unauthorized request reached signer")

    app = FastAPI()
    app.include_router(create_router(VideoService(Repo(), None, Storage())))
    app.dependency_overrides[get_current_user] = lambda: Principal("bob")
    with TestClient(app) as client:
        assert client.get("/v1/learning/videos/alice-video").status_code == 404
        playback = client.get("/v1/learning/videos/alice-video/playback")
        assert playback.status_code == 404
        assert playback.json()["error"]["code"] == "VIDEO_NOT_FOUND"


def test_worker_uses_frozen_recipe_and_stops_for_review(monkeypatch, tmp_path):
    from app.modules.videos import service
    from app.modules.videos.pipeline import generation_recipe
    from app.modules.videos.repository import LocalVideoRepository

    brief = Brief.model_validate_json(
        (ROOT / "fixtures/learning/linked-list-brief.json").read_text()
    )
    repository = LocalVideoRepository(tmp_path / "jobs.db")
    recipe = generation_recipe(fixture=True)
    job = repository.enqueue("test", "alice", brief.model_dump(), recipe)

    def generate(*args, stage, check_cancelled, **kwargs):
        check_cancelled()
        stage("rendering")
        return {"quality": {"sha256": "synthetic-hash"}}

    monkeypatch.setattr(service, "generate", generate)
    assert service.run_once(repository, tmp_path, fixture=True)
    assert repository.get(job["job_id"], "alice")["state"] == "awaiting_review"
    assert repository.ready("test", "alice") is None
    assert not service.run_once(repository, tmp_path, fixture=True)


def test_ready_video_maps_to_feed_and_authenticated_routes():
    from app.modules.videos.adapters import FeedVideoReader

    record = {
        "schema_version": "1",
        "video_id": "clip",
        "objective_id": "reverse_list",
        "lesson_request_id": "private-origin-request",
        "format_id": "visual_explainer",
        "teaching_approach": "pointer_trace",
        "level": "intro",
        "language": "en",
        "notation": "python",
        "scope": "shared_generic",
        "owner_user_id": None,
        "status": "ready",
        "title": "Reverse a list",
        "learning_goal": "Preserve successor",
        "duration_seconds": 45,
        "asset_id": "asset",
        "assets": {k: {"key": k} for k in ("video", "thumbnail", "captions")},
    }

    class Repo:
        def video(self, video_id, owner):
            return record if video_id == "clip" else None

        def list_videos(self, owner, objectives):
            return [record] if "reverse_list" in objectives else []

    class Storage:
        def signed_url(self, key):
            return "https://synthetic.example.test/" + key

    service = VideoService(Repo(), None, Storage())
    reader = FeedVideoReader(service)
    assert reader.list_variants("alice", ["reverse_list"])[0].playback.kind == "mp4"
    assert reader.resolve_playback("alice", "missing") is None
    app = FastAPI()
    app.include_router(create_router(service))
    app.dependency_overrides[get_current_user] = lambda: Principal("alice")
    with TestClient(app) as client:
        response = client.get("/v1/learning/videos/clip")
        assert response.status_code == 200
        data = response.json()
        assert data["lesson_request_id"] is None
        assert "assets" not in data and "owner_user_id" not in data
        assert data["playback"]["kind"] == "mp4"


def test_automatic_publication_cannot_publish_shared_content(tmp_path):
    brief = Brief.model_validate_json((ROOT / 'fixtures/learning/linked-list-brief.json').read_text())
    brief = brief.model_copy(update={'scope': 'shared_generic_candidate', 'owner_user_id': None})
    with pytest.raises(ValueError, match='restricted to private'):
        publish_validated_variant(None, None, {}, brief, tmp_path, {'quality': {}},
                                  {'policy': 'private_demo_automated_v1'}, automated_private=True)


def test_storage_reuses_short_lived_signatures_with_bounded_cache(monkeypatch):
    from app.modules.videos import publication
    monkeypatch.setenv("SUPABASE_URL", "https://storage.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic")
    clock = [0]
    monkeypatch.setattr(publication.time, 'monotonic', lambda: clock[0])
    calls = []
    def respond(request):
        calls.append(1)
        return httpx.Response(200, json={"signedURL": "/object/sign/test?token=" + str(len(calls))})
    storage = SupabaseVideoStorage(httpx.Client(transport=httpx.MockTransport(respond)))
    assert storage.signed_url('owned') == storage.signed_url('owned')
    assert len(calls) == 1
    clock[0] = 121
    assert storage.signed_url('owned').endswith('token=2')
