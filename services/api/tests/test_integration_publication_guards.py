"""Regression tests for slow external operations racing owner changes."""

import base64
from types import SimpleNamespace

import pytest
from test_learning_pipeline import Academics, Gemini

from app.core import collections as tables
from app.core.connections import Connections
from app.core.credential_vault import CredentialVault
from app.core.errors import APIError
from app.core.learning_pipeline import LearningPipeline, StoredQuizzes
from app.core.semantic_topics import SemanticTopics
from app.modules.videos.repository import LocalVideoRepository
from app.workers.runner import JobContext


def connections(database, before_verified=lambda: None):
    class Client:
        def __init__(self, *_):
            pass

        def get(self, _):
            before_verified()
            return {"id": 123}

    return Connections(
        database,
        CredentialVault(base64.b64encode(b"a" * 32).decode()),
        "https://school.instructure.com",
        Client,
    )


def test_canvas_disconnect_fences_inflight_token_verification(database):
    connection = connections(database, lambda: connection.disconnect("alice"))
    with pytest.raises(APIError) as error:
        connection.connect("alice", "synthetic-private-token", "connect-request")
    assert error.value.code == "CONNECTION_CHANGED"
    assert connection.public("alice")["status"] == "disconnected"
    assert database.read(lambda tx: tx.count(tables.jobs, {"owner_user_id": "alice"})) == 0


@pytest.mark.parametrize("change", ["profile", "connection"])
def test_late_embedding_cannot_publish_stale_binding_quiz_or_render(database, tmp_path, change):
    connection = connections(database)
    saved = connection.connect("alice", "synthetic-private-token")
    academics = Academics()

    def embed(_):
        if change == "connection":
            connection.disconnect("alice")
        else:
            academics.get_validated_plans = lambda _: []
        return [1.0, 0.0]

    pipeline = LearningPipeline(
        database,
        connection,
        academics,
        Gemini(),
        SemanticTopics(database, SimpleNamespace(model="fixture", embed=embed)),
        LocalVideoRepository(tmp_path / "video.db"),
    )
    context = JobContext(
        "prepare",
        "alice",
        {
            "lesson_request_id": "lr_1",
            "profile_revision": 1,
            "connection_id": saved["connection_id"],
        },
        lambda: True,
    )
    if change == "connection":
        with pytest.raises(PermissionError):
            pipeline.prepare(context)
    else:
        assert pipeline.prepare(context) == {"state": "superseded"}
    for table in [tables.topics, tables.bindings, tables.quiz_bank]:
        assert database.read(lambda tx, table=table: tx.count(table, {"user_id": "alice"})) == 0
    assert database.read(lambda tx: tx.count(tables.jobs, {"job_type": "learning.render"})) == 0


def test_retried_preparation_reuses_committed_quiz_without_model_call(database, tmp_path):
    class CountGemini(Gemini):
        calls = 0

        def generate_json(self, **kwargs):
            self.calls += 1
            return super().generate_json(**kwargs)

    client = CountGemini()
    pipeline = LearningPipeline(
        database,
        SimpleNamespace(client=lambda *args: None),
        Academics(),
        client,
        SemanticTopics(database, SimpleNamespace(model="fixture", embed=lambda _: [1.0, 0.0])),
        LocalVideoRepository(tmp_path / "video.db"),
    )
    context = JobContext(
        "prepare",
        "alice",
        {"lesson_request_id": "lr_1", "profile_revision": 1, "connection_id": "c"},
        lambda: True,
    )
    first = pipeline.prepare(context)
    assert pipeline.prepare(context)["topic_id"] == first["topic_id"]
    assert client.calls == 1
    assert len(StoredQuizzes(database).list_for_objective("alice", "obj_1")) == 1


def test_semantic_exact_key_includes_facts(database):
    calls = []

    def embed(text):
        calls.append(text)
        return [1.0, 0.0] if "linear" in text else [0.0, 1.0]

    topics = SemanticTopics(database, SimpleNamespace(model="fixture", embed=embed))
    common = {"title": "Complexity", "learning_goal": "Explain search", "subject": "CS"}
    first, _ = topics.bind("alice", "a", {**common, "facts": ["Search is linear."]})
    second, reused = topics.bind("alice", "b", {**common, "facts": ["Search is logarithmic."]})
    assert not reused and first["topic_id"] != second["topic_id"] and len(calls) == 2


def test_sync_dispatches_all_courses_and_topics_without_truncation(database, tmp_path):
    connection = connections(database)
    saved = connection.connect("alice", "synthetic-private-token")
    plans = [
        {
            "profile_revision": 1,
            "requests": [{"lesson_request_id": f"{course}_{i}"} for i in range(size)],
        }
        for course, size in [("a", 5), ("b", 3), ("c", 1)]
    ]
    academics = SimpleNamespace(
        import_profile=lambda *args, **kwargs: {"profile_id": "p", "revision": 1, "courses": []},
        get_validated_plans=lambda _: plans,
    )
    pipeline = LearningPipeline(
        database, connection, academics, None, None, LocalVideoRepository(tmp_path / "video.db")
    )
    result = pipeline.sync(
        JobContext("sync", "alice", {"connection_id": saved["connection_id"]}, lambda: True)
    )
    assert result["queued_lessons"] == 9
    jobs = database.read(
        lambda tx: tx.find(
            tables.jobs, {"job_type": "learning.prepare"}, sort=[("available_at", 1)]
        )
    )
    assert [job["input_ref"]["lesson_request_id"] for job in jobs] == [
        "a_0",
        "b_0",
        "c_0",
        "a_1",
        "b_1",
        "a_2",
        "b_2",
        "a_3",
        "a_4",
    ]


def test_explicit_retry_is_owned_idempotent_and_fenced(database):
    if database.mongo is None:
        pytest.skip("Requires API_TEST_MONGODB_URI for the cross-collection retry transaction")
    from app.core.preparation import retry_preparation
    from app.modules.videos.repository import AtlasVideoRepository

    repo = AtlasVideoRepository(database.mongo)
    repo.initialize()
    alice = repo.enqueue("alice-key", "alice", {}, {})
    bob = repo.enqueue("bob-key", "bob", {}, {})
    repo.jobs.update_many({}, {"$set": {"state": "failed", "fence": 2}})
    first = retry_preparation(database, "alice", "retry-1")
    assert first["queued_jobs"] == 1
    assert repo.get(alice["job_id"], "alice")["state"] == "queued"
    assert repo.get(alice["job_id"], "alice")["fence"] == 3
    assert repo.get(bob["job_id"], "bob")["state"] == "failed"
    repo.jobs.update_one({"job_id": alice["job_id"]}, {"$set": {"state": "failed"}})
    assert retry_preparation(database, "alice", "retry-1") == first
    assert repo.get(alice["job_id"], "alice")["state"] == "failed"
