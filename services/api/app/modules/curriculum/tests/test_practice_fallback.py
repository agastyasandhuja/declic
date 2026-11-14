"""Grounded no-deadline lessons stay distinct from expired exam material."""

from copy import deepcopy
from datetime import UTC, datetime

from app.modules.curriculum.adapters import FeedAcademicReader
from app.modules.curriculum.planning.planner import plan_course
from app.modules.curriculum.service import AcademicService
from app.modules.curriculum.store import save_profile

NOW = datetime(2026, 11, 14, 15, tzinfo=UTC)
COURSE = {
    "course_id": "c",
    "external_course_id": "100",
    "title": "Algorithms",
    "timezone": "America/New_York",
    "source_inventory": [
        {"source_id": "lecture", "resource_type": "page", "title": "Linked list lecture"},
        {"source_id": "old_exam", "resource_type": "file", "title": "Midterm solutions"},
    ],
}
UNIT = {
    "unit_id": "u",
    "course_id": "c",
    "title": "Linked lists",
    "order": 1,
    "objectives": ["Reverse a linked list"],
    "source_refs": ["lecture"],
}
PAST = {
    "assessment_id": "past",
    "course_id": "c",
    "title": "Midterm",
    "kind": "midterm",
    "source_refs": ["old_exam"],
    "scope_status": "explicit",
    "covered_topics": ["Linked lists"],
    "scheduled": {
        "date": "2026-11-13",
        "timestamp": "2026-11-13T15:00:00Z",
        "precision": "datetime",
        "timezone": "America/New_York",
        "evidence_status": "explicit",
        "source_refs": ["old_exam"],
    },
}


def publish(folder, course, units, assessments, revision=1):
    plan = plan_course(course, units, assessments, None, now=NOW)
    profile = {
        "user_id": "alice",
        "profile_id": "p",
        "revision": revision,
        "courses": [course],
        "assessments": assessments,
        "units": units,
        "_plans": [{**plan, "user_id": "alice", "profile_id": "p", "profile_revision": revision}],
    }
    save_profile(folder, "alice", profile)
    return AcademicService(folder, None, clock=lambda: NOW), profile


def test_no_deadline_course_keeps_grounded_practice_without_urgency(tmp_path):
    service, _ = publish(tmp_path, COURSE, [UNIT], [])
    request = service.get_validated_plans("alice")[0]["requests"][0]
    assert request["source_refs"] == ["lecture"]
    assert request["evidence_status"] == "suggested_practice"
    assert request["exam_scope_status"] == "unknown" and request["assessment_ids"] == []
    assert "timeline_topic" not in request
    candidates = FeedAcademicReader(service, clock=lambda: NOW).list_objectives("alice")
    assert len(candidates) == 1
    assert not candidates[0].current_unit
    assert candidates[0].assessment_date is None and candidates[0].assessment_timestamp is None
    assert FeedAcademicReader(service, clock=lambda: NOW).list_objectives("bob") == []


def test_past_assessment_alone_cannot_become_practice_but_lecture_material_can(tmp_path):
    old_unit = {**UNIT, "source_refs": ["old_exam"]}
    assert plan_course(COURSE, [old_unit], [PAST], None, now=NOW)["requests"] == []
    assert plan_course(COURSE, [], [PAST], None, now=NOW)["requests"] == []
    service, _ = publish(tmp_path, COURSE, [UNIT], [PAST])
    request = service.get_validated_plans("alice")[0]["requests"][0]
    assert request["source_refs"] == ["lecture"] and request["assessment_ids"] == []


def test_withdrawn_source_invalidates_but_new_target_does_not_hide_grounded_practice(tmp_path):
    service, profile = publish(tmp_path, deepcopy(COURSE), [UNIT], [])
    profile["courses"][0]["source_inventory"] = []
    save_profile(tmp_path, "alice", profile)
    assert service.get_validated_plans("alice") == []
    service, profile = publish(tmp_path, deepcopy(COURSE), [UNIT], [])
    future = deepcopy(PAST)
    future["scheduled"].update(date="2026-11-20", timestamp="2026-11-20T15:00:00Z")
    profile["assessments"] = [future]
    save_profile(tmp_path, "alice", profile)
    assert len(service.get_validated_plans("alice")) == 1
    candidates = FeedAcademicReader(service, clock=lambda: NOW).list_objectives("alice")
    assert len(candidates) == 1 and not candidates[0].current_unit
    assert candidates[0].assessment_date is None
