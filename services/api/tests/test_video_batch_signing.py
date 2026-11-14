"""Transport and owner-bound projections; no Supabase or model calls."""
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from app.core import collections as tables
from app.core.learning_readers import BoundVideoReader
from app.modules.videos import publication
from app.modules.videos.adapters import FeedVideoReader
from app.modules.videos.generation.providers import ProviderError
from app.modules.videos.publication import SupabaseVideoStorage
from app.modules.videos.service import VideoService


def record(vid):
    return {
        "schema_version": "1", "video_id": vid, "objective_id": "topic",
        "lesson_request_id": "request", "format_id": "visual_explainer",
        "teaching_approach": "diagram", "level": "intro", "language": "en",
        "notation": "plain", "scope": "private", "owner_user_id": "alice",
        "status": "ready", "title": "A topic", "learning_goal": "Explain",
        "duration_seconds": 45, "asset_id": vid,
        "assets": {kind: {"key": f"{vid}/{kind}"} for kind in ("video", "thumbnail", "captions")},
    }


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://storage.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic")
    monkeypatch.setenv("VIDEO_STORAGE_BUCKET", "lessons")
    calls = []
    def respond(request):
        assert request.url.path == "/storage/v1/object/sign/lessons"
        payload = json.loads(request.content)
        assert payload["expiresIn"] == 900
        calls.append(payload["paths"])
        return httpx.Response(200, json=[
            {"path": key, "error": None,
             "signedURL": f"/object/sign/lessons/{key}?token={len(calls)}"}
            for key in payload["paths"]
        ])
    return SupabaseVideoStorage(httpx.Client(transport=httpx.MockTransport(respond))), calls


def test_catalog_signs_once_without_requery_and_never_returns_other_owner_cache(storage):
    store, calls = storage
    videos = [record("one"), record("two")]
    events = []
    def listing(owner, ids):
        events.append(owner)
        return videos if owner == "alice" else []
    repo = SimpleNamespace(list_videos=listing, video=lambda vid, owner: None)
    reader = FeedVideoReader(VideoService(repo, None, store))
    result = reader.list_variants("alice", ["topic"])
    assert len(result) == 2
    assert len(calls) == 1 and len(calls[0]) == 6
    assert 599 <= (result[0].playback.expires_at - datetime.now(UTC)).total_seconds() <= 600
    assert len(reader.list_variants("alice", ["topic"])) == 2
    assert reader.list_variants("bob", ["topic"]) == []
    assert reader.get_variant("bob", "one") is None
    assert len(calls) == 1 and events == ["alice", "alice", "bob"]


def test_batch_cache_expiry_dedup_and_bound(storage, monkeypatch):
    store, calls = storage
    clock = [0.0]
    monkeypatch.setattr(publication.time, "monotonic", lambda: clock[0])
    first = store.signed_urls(["one/video", "one/video", "one/captions"])
    assert len(calls[0]) == 2
    clock[0] = 119
    assert store.signed_urls(list(first)) == first
    assert store.signed_url("one/video") == first["one/video"]
    clock[0] = 120
    assert store.signed_urls(list(first))["one/video"].endswith("token=2")
    assert len(calls) == 2
    assert store.signed_urls([]) == {}
    with pytest.raises(ValueError):
        store.signed_urls([str(i) for i in range(601)])
    assert len(calls) == 2


def test_shared_topic_bindings_sign_physical_assets_once(database, storage):
    store, calls = storage
    for owner, objective in [("alice", "course_a"), ("alice", "course_b"), ("bob", "other")]:
        database.run(owner, lambda tx, owner=owner, objective=objective: tx.insert(
            tables.bindings, {"user_id": owner, "objective_id": objective, "topic_id": "topic"}
        ))
    videos = [record("one"), record("two")]
    repo = SimpleNamespace(
        list_videos=lambda owner, ids: videos if owner == "alice" and ids == ["topic"] else [],
        video=lambda vid, owner: videos[0] if owner == "alice" else None,
    )
    reader = BoundVideoReader(VideoService(repo, None, store), database)
    results = reader.list_variants("alice", ["course_a", "course_b"])
    assert len(results) == 4
    assert len(calls) == 1 and len(calls[0]) == 6
    assert reader.get_variant_for_objective("alice", "one", "other") is None
    assert reader.get_variant_for_objective("bob", "one", "course_a") is None
    assert len(calls) == 1


@pytest.mark.parametrize("rows", [
    [], {}, [None],
    [{"path": "wanted", "signedURL": "/object/sign/lessons/wanted", "error": "missing"}],
    [{"path": "other", "signedURL": "/object/sign/lessons/other"}],
    [{"path": "wanted", "signedURL": "https://outside.test/object/sign/lessons/wanted"}],
    [{"path": "wanted", "signedURL": "/object/sign/lessons/other"}],
    [{"path": "wanted", "signedURL": "/object/sign/another/wanted"}],
])
def test_batch_rejects_partial_or_mismatched_results(storage, rows):
    store, _ = storage
    store.client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=rows))
    )
    with pytest.raises(ProviderError, match="STORAGE_SIGN_FAILED"):
        store.signed_urls(["wanted"])
    assert store._signed_cache == {}
