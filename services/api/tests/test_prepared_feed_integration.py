"""Real Mongo handoff/HTTP integration; Canvas, Gemini and media are synthetic.

This exercises the production topic/quiz persistence and video projection without
claiming real provider generation, Supabase playback or device verification.
"""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core import collections as tables
from app.core.learning_pipeline import LearningPipeline, StoredQuizzes
from app.core.learning_readers import BoundVideoReader
from app.core.semantic_topics import SemanticTopics
from app.main import create_app
from app.modules.recommendations.models import VariantCandidate
from app.modules.videos.repository import AtlasVideoRepository
from app.modules.videos.router import create_router
from app.modules.videos.service import VideoService
from app.workers.runner import JobContext
from conftest import TestIdentity, reached_quiz

OWNER = "user_demo_01"
OTHER = "user_demo_02"


class GroundedGemini:
    def generate_json(self, **kwargs):
        data = json.loads(kwargs["user_content"])
        return SimpleNamespace(
            text=json.dumps(
                {
                    "title": "Keep the next node",
                    "learning_goal": "Reverse links without losing nodes",
                    "subject": "Data structures",
                    "facts": [
                        "Save the next node before changing its link.",
                        "Point the current node to the previous node.",
                    ],
                    "source_ids": [data["sources"][0]["source_id"]],
                    "prompt": "What must be saved before changing the current link?",
                    "options": ["Next node", "List size", "Tail value"],
                    "correct_index": 0,
                    "explanation": "Saving the next node preserves access to the rest of the list.",
                }
            )
        )


class CourseSnapshot:
    def __init__(self, catalog):
        self.objectives = [
            objective.model_copy(update={"notation": "general", "title": "Reverse linked nodes"})
            for objective in catalog.objectives[:2]
        ]
        self.requests = [
            {
                "lesson_request_id": "request_" + str(i),
                "objective_id": objective.objective_id,
                "title": objective.title,
                "learning_goal": "Reverse links safely",
                "source_refs": ["source_" + str(i)],
            }
            for i, objective in enumerate(self.objectives)
        ]

    def get_validated_plans(self, owner):
        return [{"profile_revision": 1, "requests": self.requests}] if owner == OWNER else []

    def resolve_source_context(self, owner, refs):
        assert owner == OWNER
        return [
            {
                "source_id": ref,
                "text": "Save the next node, then redirect its link to the previous node.",
            }
            for ref in refs
        ]

    def list_objectives(self, owner):
        return self.objectives if owner == OWNER else []


class SignedStorage:
    def __init__(self):
        self.signed = []

    def signed_url(self, key):
        self.signed.append(key)
        return "https://synthetic-media.example.test/" + key


def test_prepared_topic_projects_into_private_feed_and_retryable_quiz(database, clock, catalog):
    if database.mongo is None:
        pytest.skip("Requires disposable API_TEST_MONGODB_URI")
    repository = AtlasVideoRepository(database.mongo)
    repository.initialize()
    academics = CourseSnapshot(catalog)
    storage = SignedStorage()
    service = VideoService(repository, academics, storage)
    reader = BoundVideoReader(service, database)
    pipeline = LearningPipeline(
        database,
        SimpleNamespace(client=lambda *args: None),
        academics,
        GroundedGemini(),
        SemanticTopics(
            database, SimpleNamespace(model="synthetic-embeddings", embed=lambda _: [1.0, 0.0])
        ),
        repository,
    )
    topics = []
    for request in academics.requests:
        result = pipeline.prepare(
            JobContext(
                "prepare",
                OWNER,
                {
                    "lesson_request_id": request["lesson_request_id"],
                    "profile_revision": 1,
                    "connection_id": "synthetic-canvas",
                },
                lambda: True,
            )
        )
        topics.append(result["topic_id"])
    assert len(set(topics)) == 1  # Same concept in two owned course bindings.
    pipeline.render(JobContext("render", OWNER, {"topic_id": topics[0]}, lambda: True))

    # Synthetic ready assets cross the real fenced catalog transaction. Actual
    # media generation/upload are tested separately; no media bytes exist here.
    video_ids = []
    for index in range(2):
        job = repository.claim()
        assert job is not None
        brief = job["brief"]
        video_id = f"prepared_variant_{index}"
        video_ids.append(video_id)
        variant = {
            **brief,
            "schema_version": "1",
            "video_id": video_id,
            "generation_key": job["generation_key"],
            "status": "ready",
            "duration_seconds": 45,
            "asset_id": f"asset_{index}",
            "assets": {
                kind: {"key": f"{video_id}/{kind}"} for kind in ["video", "thumbnail", "captions"]
            },
        }
        repository.publish(job["job_id"], job["fence"], variant)

    projections = reader.list_variants(OWNER, [o.objective_id for o in academics.objectives])
    assert len(projections) == 4
    assert all(isinstance(item, VariantCandidate) for item in projections)
    assert {item.objective_id for item in projections} == {
        o.objective_id for o in academics.objectives
    }
    assert all(item.scope == "private" and item.owner_user_id == OWNER for item in projections)
    assert all(item.playback.url.scheme == "https" for item in projections)
    before = len(storage.signed)
    assert reader.list_variants(OTHER, [o.objective_id for o in academics.objectives]) == []
    assert len(storage.signed) == before

    identity = TestIdentity()
    app = create_app(
        settings=database.settings,
        database=database,
        clock=clock,
        identity=identity,
        academics=academics,
        entertainment=catalog,
        videos=reader,
        quiz_reader=StoredQuizzes(database),
        domain_routers=(create_router(service),),
    )
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + identity.tokens[OWNER]
        sid, card, page = reached_quiz(client, clock)
        quiz = card["quiz"]
        serialized = json.dumps(page)
        for private in ["correct_option_id", "source_refs", "owner_user_id", "explanation"]:
            assert private not in serialized
        assert quiz["objective_ids"][0] in {o.objective_id for o in academics.objectives}
        assert set(quiz["related_video_ids"]).issubset(video_ids)
        # Re-read of reserved media must preserve the course objective mapping.
        cached = client.get("/v1/feed", params={"session_id": sid, "limit": 20})
        assert cached.status_code == 200, cached.text
        cached_study = [item for item in cached.json()["items"] if item["kind"] == "study_video"]
        assert len(cached_study) == 2
        for item in cached_study:
            if item["kind"] == "study_video":
                assert item["video"]["objective_id"] == item["course_context"]["objective_id"]
                assert item["video"]["objective_id"] != topics[0]
        qid = quiz["quiz_instance_id"]
        body = {"session_id": sid, "selected_option_id": "1"}
        answer_url = f"/v1/quizzes/{qid}/answers"
        assert (
            client.post(answer_url, json=body, headers={"Idempotency-Key": "answer"}).status_code
            == 409
        )
        activated = client.post(
            f"/v1/feed/sessions/{sid}/quiz-gate",
            json={"quiz_instance_id": qid, "item_id": card["item_id"]},
        )
        assert activated.status_code == 200 and activated.json()["scroll_locked"]
        result = client.post(answer_url, json=body, headers={"Idempotency-Key": "answer"})
        assert result.status_code == 200, result.text
        assert not result.json()["correct"] and result.json()["scroll_unlocked"]
        assert (
            client.post(answer_url, json=body, headers={"Idempotency-Key": "answer"}).json()
            == result.json()
        )
        assert database.read(lambda tx: tx.count(tables.attempts, {"user_id": OWNER})) == 1
        assert client.get(f"/v1/learning/videos/{video_ids[0]}/playback").status_code == 200
        before = len(storage.signed)
        client.headers["Authorization"] = "Bearer " + identity.tokens[OTHER]
        assert client.get("/v1/feed", params={"session_id": sid}).status_code == 404
        assert (
            client.post(answer_url, json=body, headers={"Idempotency-Key": "foreign"}).status_code
            == 404
        )
        assert client.get(f"/v1/learning/videos/{video_ids[0]}/playback").status_code == 404
        assert len(storage.signed) == before
