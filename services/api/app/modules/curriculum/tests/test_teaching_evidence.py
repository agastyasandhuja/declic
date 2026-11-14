"""Scheduling evidence must not become teaching facts or conceptual quizzes."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.curriculum.planning.planner import plan_course
from app.modules.curriculum.source_quality import InsufficientTeachingEvidence, teaching_text
from app.modules.quizzes.generation import prepare_lesson

NOW = datetime(2026, 11, 14, tzinfo=UTC)
COURSE = {"course_id": "c", "external_course_id": "100", "timezone": "UTC"}
CONCEPT = {
    "source_id": "lecture",
    "course_id": "c",
    "resource_type": "file",
    "title": "Chapter 17 cash flows",
    "text": "An annuity is a series of equal cash flows at regular intervals. "
    "Discounting a future cash flow converts its value into a present value.",
}
TARGET = {
    "assessment_id": "a",
    "course_id": "c",
    "title": "Homework: Cash flows",
    "kind": "assignment",
    "source_refs": ["assignment"],
    "scope_status": "unknown",
    "covered_topics": [],
    "scheduled": {
        "date": "2026-11-16",
        "timestamp": "2026-11-16T15:00:00Z",
        "precision": "datetime",
        "timezone": "UTC",
        "evidence_status": "explicit",
        "source_refs": ["assignment"],
    },
}
ADMIN = {
    "source_id": "assignment",
    "course_id": "c",
    "resource_type": "assignment",
    "title": "Chapter 17 SmartBook",
    "text": "Chapter 17 SmartBook is an assignment. It is due November 16.",
}
REQUEST = {"title": "Cash flows", "learning_goal": "Explain cash flow timing"}
LESSON = {
    "title": "Cash flow timing",
    "learning_goal": "Compare present and future cash flows",
    "subject": "Finance",
    "facts": [
        "An annuity has equally spaced equal cash flows.",
        "Discounting converts a future value into a present value.",
    ],
    "source_ids": ["lecture"],
    "prompt": "What does discounting calculate?",
    "options": ["Present value", "Number of payments", "Payment date"],
    "correct_index": 0,
    "explanation": "Discounting expresses a future amount as its value today.",
}


def test_administrative_sources_never_reach_gemini():
    client = SimpleNamespace(generate_json=lambda **_: pytest.fail("No paid model call expected"))
    for source in [ADMIN, {**ADMIN, "resource_type": "page", "title": "Course navigation"}]:
        with pytest.raises(InsufficientTeachingEvidence):
            prepare_lesson(client, REQUEST, [source])


def test_schedule_only_plan_is_unavailable_but_matching_lecture_supports_it():
    empty = plan_course(COURSE, [], [TARGET], None, [ADMIN], now=NOW)
    assert empty["requests"] == [] and "unavailable" in empty["warnings"][0]
    plan = plan_course(COURSE, [], [TARGET], None, [ADMIN, CONCEPT], now=NOW)
    assert len(plan["requests"]) == 1
    assert plan["requests"][0]["source_refs"] == ["lecture"]
    assert plan["requests"][0]["assessment_ids"] == ["a"]


def test_unrelated_lecture_does_not_ground_assignment_topic():
    unrelated = {**CONCEPT, "title": "Binary search trees"}
    assert plan_course(COURSE, [], [TARGET], None, [ADMIN, unrelated], now=NOW)["requests"] == []


def test_assignment_without_teaching_content_does_not_block_lecture_practice():
    course = {**COURSE, "source_inventory": [CONCEPT]}
    unit = {
        "unit_id": "u",
        "course_id": "c",
        "title": "Annuities",
        "order": 1,
        "objectives": ["Annuity cash flow timing"],
        "source_refs": ["lecture"],
    }
    target = deepcopy(TARGET)
    target["title"] = "Homework: Binary trees"
    plan = plan_course(course, [unit], [target], None, [ADMIN, CONCEPT], now=NOW)
    assert len(plan["requests"]) == 1
    request = plan["requests"][0]
    assert request["source_refs"] == ["lecture"] and request["assessment_ids"] == []
    assert request["evidence_status"] == "suggested_practice"


@pytest.mark.parametrize(
    "patch",
    [
        {"title": "Insufficient Course Material"},
        {"facts": []},
        {"facts": ["Chapter 17 is an assignment.", "The assignment is due November 16."]},
    ],
)
def test_model_placeholder_or_administrative_facts_are_unavailable(patch):
    client = SimpleNamespace(
        generate_json=lambda **_: SimpleNamespace(text=json.dumps({**LESSON, **patch}))
    )
    with pytest.raises(InsufficientTeachingEvidence):
        prepare_lesson(client, REQUEST, [CONCEPT])


def test_concept_lesson_receives_only_teaching_excerpt_and_allows_empty_insufficient_response():
    def generate(**kwargs):
        data = json.loads(kwargs["user_content"])
        assert [source["source_id"] for source in data["sources"]] == ["lecture"]
        assert (
            "minItems" not in kwargs["response_schema"]["properties"]["facts"]
            or kwargs["response_schema"]["properties"]["facts"]["minItems"] == 0
        )
        return SimpleNamespace(text=json.dumps(LESSON))

    assert (
        prepare_lesson(SimpleNamespace(generate_json=generate), REQUEST, [ADMIN, CONCEPT]).facts
        == LESSON["facts"]
    )
    assert (
        " ".join(
            teaching_text(
                {**CONCEPT, "text": CONCEPT["text"] + "\nHomework is due tomorrow."}
            ).split()
        )
        == CONCEPT["text"]
    )


@pytest.mark.parametrize(
    "title,facts",
    [
        (
            "Annuity due",
            [
                "An annuity due makes payments at the beginning of each period.",
                "An ordinary annuity makes payments at the end of each period.",
            ],
        ),
        (
            "Assignment operators",
            [
                "An assignment operator stores a value in a variable.",
                "A compound assignment operator combines an operation with assignment.",
            ],
        ),
        (
            "Insufficient funds",
            [
                "Insufficient funds means a balance cannot cover a requested payment.",
                "A bank may reject a payment when the available balance is too low.",
            ],
        ),
    ],
)
def test_conceptual_uses_of_administrative_words_remain_teachable(title, facts):
    source = {**CONCEPT, "title": title, "text": " ".join(facts)}
    client = SimpleNamespace(
        generate_json=lambda **_: SimpleNamespace(
            text=json.dumps({**LESSON, "title": title, "facts": facts})
        )
    )
    assert teaching_text(source)
    assert prepare_lesson(client, {**REQUEST, "title": title}, [source]).facts == facts
