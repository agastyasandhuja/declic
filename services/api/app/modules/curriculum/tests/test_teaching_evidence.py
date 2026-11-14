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


def test_learning_outcomes_are_not_conceptual_facts_or_source_evidence():
    facts = [
        "Students will learn how to explain effects on the accounting equation.",
        "Students will learn how to distinguish cash and accrual accounting.",
    ]
    source = {**CONCEPT, "title": "Course objectives", "text": " ".join(facts)}
    assert teaching_text(source) == ""
    assert teaching_text({**CONCEPT, "title": "Fall course syllabus.pdf"}) == ""
    client = SimpleNamespace(
        generate_json=lambda **_: SimpleNamespace(text=json.dumps({**LESSON, "facts": facts}))
    )
    with pytest.raises(InsufficientTeachingEvidence):
        prepare_lesson(client, REQUEST, [CONCEPT])


def test_missing_unit_map_recovers_grounded_concepts_with_one_bounded_call(tmp_path):
    from app.modules.curriculum.planning.planner import build_lesson_plans

    facts = [
        "An annuity is a series of equal cash flows at regular intervals.",
        "Discounting a future cash flow converts its value into a present value.",
    ]
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            text=json.dumps(
                {
                    "lessons": [
                        {
                            "title": "Cash flow timing",
                            "evidence": [{"source_id": "lecture", "quote": fact} for fact in facts],
                        }
                    ]
                }
            )
        )

    profile = {
        "profile_id": "p",
        "revision": 1,
        "user_id": "alice",
        "units": [],
        "unit_ids": [],
        "assessments": [],
        "courses": [{**COURSE, "import_status": "partial", "source_inventory": [CONCEPT]}],
    }
    resolver = SimpleNamespace(sources_for_course=lambda course_id: [CONCEPT])
    plans = build_lesson_plans(profile, SimpleNamespace(generate_json=generate), resolver)
    assert len(calls) == 1 and len(plans[0]["requests"]) == 1
    request = plans[0]["requests"][0]
    assert request["source_refs"] == ["lecture"] and request["assessment_ids"] == []
    assert (
        request["evidence_status"] == "suggested_practice"
        and request["exam_scope_status"] == "unknown"
    )
    assert request["unit_id"] in profile["unit_ids"]
    assert profile["units"][0]["objectives"] == ["Cash flow timing"]
    # Once grounded units exist, planning reuses them without another model call.
    assert build_lesson_plans(profile, SimpleNamespace(generate_json=generate), resolver)[0][
        "requests"
    ]
    assert len(calls) == 1


@pytest.mark.parametrize(
    "evidence",
    [
        [{"source_id": "foreign", "quote": CONCEPT["text"]}] * 2,
        [
            {
                "source_id": "lecture",
                "quote": "This invented quotation never occurs in the source document.",
            }
        ]
        * 2,
        [{"source_id": "lecture", "quote": CONCEPT["text"]}] * 2,
    ],
)
def test_discovery_cannot_invent_support_or_use_foreign_source(evidence):
    from app.modules.curriculum.planning.planner import discover_practice_units

    client = SimpleNamespace(
        generate_json=lambda **_: SimpleNamespace(
            text=json.dumps({"lessons": [{"title": "Cash flow timing", "evidence": evidence}]})
        )
    )
    assert discover_practice_units("c", [CONCEPT], client) == []


def test_discovery_skips_model_when_only_outcomes_or_schedule_is_available():
    from app.modules.curriculum.planning.planner import discover_practice_units

    client = SimpleNamespace(generate_json=lambda **_: pytest.fail("No model call expected"))
    assert discover_practice_units("c", [ADMIN], client) == []


def test_short_pdf_lines_and_formulas_preserve_teaching_content():
    source = {
        **CONCEPT,
        "title": "Expected value lecture.pdf",
        "text": "Expected value\nE[X] = sum(x * P(X=x))\nMultiply each possible value\n"
        "by its probability.\nAdd these weighted values\nto obtain the expectation.\nPage 2",
    }
    retained = teaching_text(source)
    assert "E[X] = sum(x * P(X=x))" in retained
    assert "Multiply each possible value" in retained and "by its probability." in retained
    assert "Page 2" not in retained


def test_publisher_chap_filename_matches_only_requested_chapter():
    from app.modules.curriculum.source_quality import matching_teaching_refs

    chapter17 = {**CONCEPT, "title": "williams_finman_20e_chap17_Accessibility.pptx"}
    chapter1 = {
        **CONCEPT,
        "source_id": "unrelated",
        "title": "williams_finman_20e_chap01_Accessibility.pptx",
    }
    assert matching_teaching_refs("Ch.17 Homework", [], [chapter17, chapter1]) == ["lecture"]
    assert matching_teaching_refs("Chapter 17", [], [chapter1]) == []
    assert matching_teaching_refs("Chapter 1", [], [chapter1]) == ["unrelated"]


def test_only_exact_authorized_inline_citations_are_removed_from_visible_text():
    from app.modules.quizzes.generation import strip_authorized_citations

    payload = {
        **LESSON,
        "facts": [fact + " [lecture]" for fact in LESSON["facts"]],
        "prompt": LESSON["prompt"] + " [lecture]",
        "options": [option + " [lecture]" for option in LESSON["options"]],
        "explanation": LESSON["explanation"] + " [lecture]",
    }
    client = SimpleNamespace(generate_json=lambda **_: SimpleNamespace(text=json.dumps(payload)))
    lesson = prepare_lesson(client, REQUEST, [CONCEPT])
    assert lesson.facts == LESSON["facts"] and lesson.prompt == LESSON["prompt"]
    assert lesson.options == LESSON["options"] and lesson.explanation == LESSON["explanation"]
    assert lesson.source_ids == ["lecture"]
    assert strip_authorized_citations(
        {"facts": ["Keep [other] and [lecture-extra] [lecture]."], "source_ids": ["lecture"]},
        {"lecture"},
    ) == {"facts": ["Keep [other] and [lecture-extra] ."], "source_ids": ["lecture"]}


@pytest.mark.parametrize(
    "fact",
    [
        "The symbol ∢ represents the union of two sets.",
        "The union of sets is written with the angle symbol ∠.",
        "The symbol � indicates the intersection of two sets.",
        "The operation uses the symbol \ue001 between the sets.",
    ],
)
def test_garbled_or_conflicting_pdf_notation_is_unavailable(fact):
    client = SimpleNamespace(
        generate_json=lambda **_: SimpleNamespace(
            text=json.dumps(
                {
                    **LESSON,
                    "facts": [fact, "The intersection contains elements shared by both sets."],
                }
            )
        )
    )
    with pytest.raises(InsufficientTeachingEvidence):
        prepare_lesson(client, REQUEST, [CONCEPT])


def test_garbled_source_can_support_verbal_concept_but_not_invented_corrected_symbol():
    source = {
        **CONCEPT,
        "title": "Set operations",
        "text": "The union contains elements belonging to either set. "
        "The intersection contains elements shared by both sets. Symbol: ∢",
    }
    facts = [
        "The union contains elements belonging to either set.",
        "The intersection contains elements shared by both sets.",
    ]
    response = {**LESSON, "title": "Set operations", "facts": facts}

    def generate(**kwargs):
        assert "Never infer or silently correct" in kwargs["system_instruction"]
        return SimpleNamespace(text=json.dumps(response))

    client = SimpleNamespace(generate_json=generate)
    assert prepare_lesson(client, REQUEST, [source]).facts == facts
    response["facts"] = ["The union symbol ∪ combines the elements of both sets.", facts[1]]
    with pytest.raises(InsufficientTeachingEvidence, match="notation"):
        prepare_lesson(client, REQUEST, [source])
    assert (
        prepare_lesson(
            client, REQUEST, [{**source, "text": source["text"].replace("∢", "∪")}]
        ).facts
        == response["facts"]
    )
