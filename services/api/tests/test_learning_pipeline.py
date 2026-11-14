import json
from types import SimpleNamespace

import pytest

from app.core.learning_pipeline import LearningPipeline, StoredQuizzes
from app.core.semantic_topics import SemanticTopics
from app.modules.quizzes.generation import prepare_lesson
from app.modules.videos.repository import LocalVideoRepository
from app.workers.runner import JobContext


class Gemini:
    def generate_json(self, **kwargs):
        assert "untrusted" in kwargs["system_instruction"]
        return SimpleNamespace(
            text=json.dumps(
                {
                    "title": "Preserve the next node",
                    "learning_goal": "Reverse links without losing nodes",
                    "subject": "Data structures",
                    "facts": [
                        "Save the next node before mutation.",
                        "Redirect the current link to the previous node.",
                    ],
                    "source_ids": ["source_1"],
                    "prompt": "What must be saved before changing the link?",
                    "options": ["Next node", "List size", "Tail value"],
                    "correct_index": 0,
                    "explanation": "The next node preserves access to the unprocessed list.",
                }
            )
        )


class Academics:
    request = {
        "lesson_request_id": "lr_1",
        "objective_id": "obj_1",
        "title": "Reverse a list",
        "learning_goal": "Reverse links",
        "source_refs": ["source_1"],
    }

    def get_validated_plans(self, owner):
        return [{"profile_revision": 1, "requests": [self.request]}]

    def resolve_source_context(self, owner, refs):
        return [
            {"source_id": "source_1", "text": "Save the next node then redirect the current link."}
        ]


def test_handoff_prepares_private_quiz_and_deduplicated_video_jobs(database, tmp_path):
    embeddings = SimpleNamespace(model="fake", embed=lambda _: [1.0, 0.0])
    repository = LocalVideoRepository(tmp_path / "videos.db")
    pipeline = LearningPipeline(
        database,
        SimpleNamespace(client=lambda *args: None),
        Academics(),
        Gemini(),
        SemanticTopics(database, embeddings),
        repository,
    )
    context = JobContext(
        "job",
        "alice",
        {"lesson_request_id": "lr_1", "profile_revision": 1, "connection_id": "connection"},
        lambda: True,
    )
    result = pipeline.prepare(context)
    assert pipeline.prepare(context)["topic_id"] == result["topic_id"]
    quizzes = StoredQuizzes(database).list_for_objective("alice", "obj_1")
    assert len(quizzes) == 1
    assert StoredQuizzes(database).list_for_objective("bob", "obj_1") == []
    assert "correct_option_id" not in quizzes[0].card("instance", [])
    rendering = JobContext("render", "alice", {"topic_id": result["topic_id"]}, lambda: True)
    jobs = pipeline.render(rendering)["video_job_ids"]
    assert pipeline.render(rendering)["video_job_ids"] == jobs
    assert len(jobs) == 2
    reteach = JobContext("reteach", "alice", {"objective_id": "obj_1"}, lambda: True)
    assert pipeline.reteach(reteach)["video_job_ids"] == jobs
    assert pipeline.reteach(
        JobContext("other", "bob", {"objective_id": "obj_1"}, lambda: True)
    ) == {"state": "topic_unavailable"}
    assert all(repository.get(job, "alice")["brief"]["scope"] == "private" for job in jobs)
    assert all(repository.get(job, "bob") is None for job in jobs)


def test_model_cannot_invent_source_references():
    with pytest.raises(ValueError):
        prepare_lesson(
            Gemini(), Academics.request, [{"source_id": "different", "text": "Other text"}]
        )


def test_administrative_sources_and_cached_placeholders_cannot_publish(database, tmp_path):
    from app.core import collections as tables

    academics = Academics()
    repository = LocalVideoRepository(tmp_path / "quality.db")
    pipeline = LearningPipeline(
        database,
        SimpleNamespace(client=lambda *args: None),
        academics,
        Gemini(),
        SemanticTopics(database, SimpleNamespace(model="fake", embed=lambda _: [1.0, 0.0])),
        repository,
    )
    context = JobContext(
        "job",
        "alice",
        {"lesson_request_id": "lr_1", "profile_revision": 1, "connection_id": "connection"},
        lambda: True,
    )
    prepared = pipeline.prepare(context)
    topic_id = prepared["topic_id"]
    database.run(
        "alice",
        lambda tx: tx.update(
            tables.topics,
            {"user_id": "alice", "topic_id": topic_id},
            {"lesson": {"title": "Insufficient Course Material", "facts": []}},
        ),
    )
    assert pipeline.prepare(context) == {
        "state": "unavailable",
        "reason": "INSUFFICIENT_TEACHING_EVIDENCE",
    }
    assert StoredQuizzes(database).list_for_objective("alice", "obj_1") == []
    assert (
        pipeline.render(JobContext("render", "alice", {"topic_id": topic_id}, lambda: True))[
            "state"
        ]
        == "unavailable"
    )
    academics.resolve_source_context = lambda *_: [
        {
            "source_id": "source_1",
            "resource_type": "assignment",
            "text": "Chapter 17 exists and the assignment is due tomorrow.",
        }
    ]
    pipeline.client = SimpleNamespace(
        generate_json=lambda **_: pytest.fail("No model call expected")
    )
    assert pipeline.prepare(context)["state"] == "unavailable"


def test_stale_insufficient_job_does_not_disable_new_revision_quiz(database, tmp_path):
    from app.core import collections as tables

    pipeline = LearningPipeline(
        database,
        SimpleNamespace(client=lambda *args: None),
        Academics(),
        Gemini(),
        SemanticTopics(database, SimpleNamespace(model="fake", embed=lambda _: [1.0, 0.0])),
        LocalVideoRepository(tmp_path / "stale-quality.db"),
    )
    context = JobContext(
        "job",
        "alice",
        {"lesson_request_id": "lr_1", "profile_revision": 1, "connection_id": "connection"},
        lambda: True,
    )
    pipeline.prepare(context)
    database.run(
        "alice",
        lambda tx: tx.update(
            tables.quiz_bank, {"user_id": "alice", "objective_id": "obj_1"}, {"profile_revision": 2}
        ),
    )
    pipeline._unavailable(context, "obj_1")
    assert (
        database.read(
            lambda tx: tx.find_one(
                tables.quiz_bank,
                {"user_id": "alice", "objective_id": "obj_1", "profile_revision": 2},
            )
        )["active"]
        is True
    )
