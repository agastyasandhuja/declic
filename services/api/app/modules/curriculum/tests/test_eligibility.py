"""Regression checks for time and evidence at generation and feed boundaries."""
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from app.modules.curriculum.planning.planner import plan_course
from app.modules.curriculum.service import AcademicService
from app.modules.curriculum.store import save_profile
from app.modules.curriculum.timing import assessment_topics, priority_targets, upcoming_assessments
from app.modules.curriculum.validators import validate_extraction

NOW = datetime(2026, 11, 14, 15, tzinfo=timezone.utc)
COURSE = {"course_id": "course", "external_course_id": "100", "timezone": "America/New_York"}
def target(identifier, title, timestamp, **extra):
    return {
        "assessment_id": identifier, "course_id": "course", "title": title, "kind": "assignment",
        "source_refs": ["source"], "scope_status": "unknown", "covered_topics": [],
        "scheduled": {"date": timestamp[:10], "timestamp": timestamp,
                      "precision": "datetime", "timezone": "America/New_York",
                      "evidence_status": "explicit", "source_refs": ["source"]},
        **extra,
    }


class EligibilityTests(unittest.TestCase):
    def test_exact_deadline_and_missing_offsets(self):
        values = [
            target("past", "HW: Heaps", "2026-11-14T14:59:59Z"),
            target("equal", "HW: Heaps", "2026-11-14T15:00:00Z"),
            target("naive", "HW: Heaps", "2026-11-14T16:00:00"),
            target("future", "HW: Heaps", "2026-11-14T10:00:01-05:00"),
        ]
        self.assertEqual([x["assessment_id"] for x in upcoming_assessments(values, NOW)], ["future"])

    def test_date_only_in_local_zone_and_missing_zone(self):
        item = target("date", "HW: Heaps", "2026-11-14T00:00:00Z")
        item["scheduled"].update(timestamp=None, precision="date")
        self.assertTrue(upcoming_assessments([item], datetime(2026, 11, 15, 4, 59, tzinfo=timezone.utc)))
        self.assertFalse(upcoming_assessments([item], datetime(2026, 11, 15, 5, tzinfo=timezone.utc)))
        item["scheduled"]["timezone"] = None
        self.assertFalse(upcoming_assessments([item], NOW))

    def test_dst_transition(self):
        item = target("date", "HW: Heaps", "2026-11-01T00:00:00Z")
        item["scheduled"].update(timestamp=None, precision="date")
        self.assertTrue(upcoming_assessments([item], datetime(2026, 11, 2, 4, 59, tzinfo=timezone.utc)))
        self.assertFalse(upcoming_assessments([item], datetime(2026, 11, 2, 5, tzinfo=timezone.utc)))

    def test_conflicting_and_inferred_dates(self):
        item = target("exam", "Midterm", "2026-11-16T15:00:00Z", kind="midterm",
                      covered_topics=["Heaps"], scope_status="explicit", date_conflict=True)
        self.assertFalse(upcoming_assessments([item], NOW))
        item.pop("date_conflict")
        item["scheduled"]["evidence_status"] = "inferred"
        self.assertFalse(upcoming_assessments([item], NOW))

    def test_nearer_coursework_survives_exam_priority(self):
        items = [
            target("hw", "PA11 Heaps and Treaps", "2026-11-16T15:00:00Z"),
            target("exam", "Midterm", "2026-11-20T15:00:00Z", kind="midterm",
                   covered_topics=["Hash tables"], scope_status="explicit"),
            target("later", "PA12 Sorting", "2026-12-01T15:00:00Z"),
        ]
        self.assertEqual([item["assessment_id"] for item in priority_targets(items, NOW)], ["exam", "hw"])

    def test_generic_and_administrative_titles(self):
        for title in ["HW 16.1", "Quiz 8", "Homework 5 Collaboration/LLM Acknowledgements",
                      "Chapter 10", "🏗️ Challenge 01 Starter Project"]:
            self.assertEqual(assessment_topics({"kind": "assignment", "title": title}), [], title)
        self.assertEqual(assessment_topics({"kind": "quiz", "title": "🛠️ Quiz 10: String I/O"}), ["String I/O"])

    def test_shared_topic_survives_first_deadline_then_expires(self):
        items = [target("a", "HW: Heaps", "2026-11-15T15:00:00Z"),
                 target("b", "Quiz: Heaps", "2026-11-16T15:00:00Z")]
        plan = plan_course(COURSE, [], items, None, now=NOW)
        self.assertEqual(len(plan["requests"]), 1)
        self.assertEqual(plan["requests"][0]["assessment_ids"], ["a", "b"])
        with tempfile.TemporaryDirectory() as folder:
            profile = {"user_id": "owner", "profile_id": "profile", "revision": 1,
                       "courses": [COURSE], "assessments": items,
                       "_plans": [{**plan, "user_id": "owner", "profile_id": "profile", "profile_revision": 1}]}
            save_profile(Path(folder), "owner", profile)
            service = AcademicService(Path(folder), None,
                                      clock=lambda: datetime(2026, 11, 15, 16, tzinfo=timezone.utc))
            self.assertEqual(service.get_validated_plans("owner")[0]["requests"][0]["assessment_ids"], ["b"])
            self.assertEqual(service.get_validated_plans("other"), [])
            service.clock = lambda: datetime(2026, 11, 16, 16, tzinfo=timezone.utc)
            self.assertEqual(service.get_validated_plans("owner"), [])

    def test_scope_cannot_leak_between_similarly_named_exams(self):
        raw = {"assessments": [{"title": "Midterm 2", "kind": "midterm", "scope_status": "explicit",
                               "source_ids": ["s"], "covered_topics": ["heaps"]}]}
        for evidence in ["Midterm 20 covers heaps.", "Midterm 2 does not cover heaps.",
                         "Midterm 2 covers sorting, excluding heaps."]:
            result = validate_extraction(deepcopy(raw), {"s"}, evidence={"s": evidence})
            self.assertEqual(result["assessments"][0]["covered_topics"], [], evidence)

    def test_canvas_dates_survive_model_failure_and_manual_corrections(self):
        from app.modules.canvas.assignments import Assignment
        from app.modules.curriculum.client.gemini import GeminiError
        from app.modules.curriculum.extract import build_profile
        from app.modules.curriculum.sources import ResolvedSource

        class CanvasSnapshot:
            owner_user_id = "owner"

            def course_ids(self):
                return ["course"]

            def course_info(self, course_id):
                return {**COURSE, "title": "Data Structures"}

            def sources_for_course(self, course_id):
                return [ResolvedSource("source", "course", "PA11 Heaps and Treaps",
                                       "assignment", "canvas", "Heaps and Treaps", external_id="a")]

            def assignments_for_course(self, course_id):
                return [Assignment("a", "PA11 Heaps and Treaps", "2026-11-20T15:00:00Z", None)]

        class UnavailableModel:
            def generate_json(self, **kwargs):
                raise GeminiError("unavailable")

        with tempfile.TemporaryDirectory() as folder:
            profile = build_profile("owner", CanvasSnapshot(), UnavailableModel(), Path(folder))
            self.assertEqual(profile["courses"][0]["import_status"], "partial")
            self.assertEqual(profile["assessments"][0]["scheduled"]["timestamp"],
                             "2026-11-20T10:00:00-05:00")
            service = AcademicService(Path(folder), None)
            service.apply_corrections("owner", 1, [{
                "assessment_id": profile["assessments"][0]["assessment_id"], "date": None,
            }])
            updated = build_profile("owner", CanvasSnapshot(), UnavailableModel(), Path(folder))
            self.assertEqual(updated["revision"], 3)
            self.assertIsNone(updated["assessments"][0]["scheduled"]["date"])
            self.assertEqual(plan_course(COURSE, [], updated["assessments"], None, now=NOW)["requests"], [])
