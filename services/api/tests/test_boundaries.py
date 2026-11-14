from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.core import collections
from app.core.config import Settings
from app.core.identity import FixtureIdentity
from app.core.migrate import apply
from conftest import reached_quiz


def test_cached_feed_drops_revoked_or_unready_study_video(client, catalog):
    sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    original = client.get("/v1/feed", params={"session_id": sid}).json()
    study = next(i for i in original["items"] if i["kind"] == "study_video")
    catalog.variants = [v.model_copy(update={"status": "failed"}) for v in catalog.variants]
    replay = client.get("/v1/feed", params={"session_id": sid}).json()
    assert study["item_id"] not in {i["item_id"] for i in replay["items"]}
    assert replay["availability"]["entertainment"] == "ready"
    assert all(i["kind"] == "entertainment_video" for i in replay["items"])


def test_cached_playback_is_refreshed_by_id(client, catalog, clock, monkeypatch):
    sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    page = client.get("/v1/feed", params={"session_id": sid}).json()
    study = next(i for i in page["items"] if i["kind"] == "study_video")
    video_id = study["video"]["video_id"]
    original = catalog.get_variant("user_demo_01", video_id)
    expired = original.model_copy(
        update={"playback": original.playback.model_copy(update={"expires_at": clock()})}
    )
    catalog.variants = [expired if v.video_id == video_id else v for v in catalog.variants]
    fresh = original.playback.model_copy(update={"expires_at": clock() + timedelta(minutes=15)})
    monkeypatch.setattr(catalog, "resolve_playback", lambda user, video: fresh)
    replay = client.get("/v1/feed", params={"session_id": sid}).json()
    returned = next(i for i in replay["items"] if i["kind"] == "study_video")
    assert returned["item_id"] == study["item_id"]
    assert returned["video"]["playback"]["expires_at"] is not None


def test_unbounded_prefetch_is_rejected(client):
    sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    params = {"session_id": sid, "limit": 20}
    first = client.get("/v1/feed", params=params).json()
    second = client.get("/v1/feed", params={**params, "cursor": first["next_cursor"]}).json()
    blocked = client.get("/v1/feed", params={**params, "cursor": second["next_cursor"]})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "FEED_BUFFER_FULL"


def test_withdrawn_cached_items_release_buffer_without_credit(client, catalog, clock):
    sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    params = {"session_id": sid, "limit": 20}
    first = client.get("/v1/feed", params=params).json()
    second = client.get("/v1/feed", params={**params, "cursor": first["next_cursor"]}).json()
    assert len(first["items"]) == len(second["items"]) == 20
    clips, variants = catalog.clips, catalog.variants
    catalog.clips, catalog.variants = [], []
    removed = client.get("/v1/feed", params=params)
    assert removed.status_code == 200
    assert removed.json()["items"] == []

    # Returning media gets new occurrences; a stale client cannot report viewing
    # a withdrawn occurrence or manufacture learning credit for its removal.
    catalog.clips, catalog.variants = clips, variants
    replacement = client.get("/v1/feed", params={**params, "cursor": second["next_cursor"]})
    assert replacement.status_code == 200, replacement.text
    assert len(replacement.json()["items"]) == 20
    assert not {i["item_id"] for i in first["items"]} & {
        i["item_id"] for i in replacement.json()["items"]
    }
    event = client.post(
        "/v1/feed/events",
        json=[
            {
                "event_id": "withdrawn-start",
                "session_id": sid,
                "item_id": first["items"][0]["item_id"],
                "event_type": "playback_started",
                "client_occurred_at": clock().isoformat(),
                "payload": {"position_ms": 0, "visible_watch_ms": 0},
            }
        ],
    )
    assert event.json()["rejected"] == [{"event_id": "withdrawn-start", "code": "ITEM_UNAVAILABLE"}]
    resumed = client.post("/v1/feed/sessions", json={"resume_session_id": sid}).json()
    assert resumed["active_view_seconds"] == 0
    blocked = client.get("/v1/feed", params={**params, "cursor": replacement.json()["next_cursor"]})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "FEED_BUFFER_FULL"


def test_missing_alternate_explanation_enqueues_reference_only_job(
    client, clock, catalog, database
):
    sid, quiz, _ = reached_quiz(client, clock)
    qid = quiz["quiz"]["quiz_instance_id"]
    catalog.variants = []
    client.post(
        f"/v1/feed/sessions/{sid}/quiz-gate",
        json={
            "quiz_instance_id": qid,
            "item_id": quiz["item_id"],
        },
    )
    response = client.post(
        f"/v1/quizzes/{qid}/answers",
        headers={"Idempotency-Key": "missing"},
        json={"session_id": sid, "selected_option_id": "b"},
    )
    assert response.status_code == 200
    with database.transaction() as unit:
        jobs = unit.find(collections.jobs, {"owner_user_id": "user_demo_01"})
        assert len(jobs) == 1
        assert set(jobs[0]["input_ref"]) == {
            "objective_id",
            "learning_revision",
            "quiz_instance_id",
        }
        assert jobs[0]["state"] == "queued"


def test_quiz_transaction_rolls_back_if_outbox_write_fails(
    client, clock, app, database, monkeypatch
):
    sid, quiz, _ = reached_quiz(client, clock)
    qid = quiz["quiz"]["quiz_instance_id"]
    app.state.feed.activate_gate("user_demo_01", sid, qid, quiz["item_id"])
    import app.modules.quizzes.service as service
    from app.modules.quizzes.schemas import AnswerRequest

    def fail(*args, **kwargs):
        raise RuntimeError("test storage failure")

    monkeypatch.setattr(service, "publish", fail)
    with pytest.raises(RuntimeError):
        app.state.quizzes.answer(
            "user_demo_01", qid, AnswerRequest(session_id=sid, selected_option_id="a"), "rollback"
        )
    with database.transaction() as unit:
        assert unit.count(collections.attempts) == 0
        assert unit.count(collections.learning) == 0
        assert unit.find_one(collections.quiz_instances, {"instance_id": qid})["state"] == "pending"


def test_production_rejects_fake_persistence_and_insecure_tls():
    with pytest.raises(ValidationError):
        Settings(environment="production", persistence="fixture_sqlite", _env_file=None)
    with pytest.raises(ValidationError):
        Settings(
            environment="production", mongodb_uri="mongodb://localhost/?tls=false", _env_file=None
        )
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            mongodb_uri="mongodb+srv://example.invalid/?tlsInsecure=true",
            _env_file=None,
        )
    with pytest.raises(ValueError):
        FixtureIdentity(Settings(environment="test", persistence="fixture_sqlite", _env_file=None))


def test_schema_setup_is_repeatable_and_enforces_unique_attempt(database):
    if database.mongo is None:
        pytest.skip("Real MongoDB verification requires API_TEST_MONGODB_URI")
    from pymongo.errors import DuplicateKeyError, WriteError

    apply(database)
    apply(database)
    database.verify_ready()
    row = {"attempt_id": "one", "instance_id": "same", "user_id": "user_demo_01", "data": {}}
    database.mongo[collections.attempts].insert_one(row)
    row.pop("_id", None)
    with pytest.raises(DuplicateKeyError):
        database.mongo[collections.attempts].insert_one({**row, "attempt_id": "two"})
    with pytest.raises(WriteError):
        database.mongo[collections.attempts].insert_one({"attempt_id": "missing-owner"})
