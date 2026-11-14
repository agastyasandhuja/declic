import json
import unittest

from app.modules.curriculum.client.gemini import GeminiClient
from app.modules.curriculum.config import GeminiSettings
from app.modules.curriculum.planning.planner import build_lesson_plans, plan_course


def settings():
    return GeminiSettings.from_env({"GEMINI_API_KEY": "k", "GEMINI_MODEL": "m"})


def plan_response(lessons):
    body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps({"lessons": lessons})}]}}],
            "usageMetadata": {}}
    return 200, json.dumps(body).encode()


def client(lessons):
    return GeminiClient(settings(), transport=lambda *a: plan_response(lessons))


COURSE = {"course_id": "c1", "title": "DSA", "term": "Fall 2026", "import_status": "ready"}
UNITS = [{"course_id": "c1", "unit_id": "u1", "title": "Linked lists", "order": 2,
          "objectives": ["reversal"], "source_refs": ["src_canvas_c1_syllabus"]}]
ASSESSMENTS = [{"course_id": "c1", "assessment_id": "a1", "title": "Midterm 1", "kind": "midterm",
                "scheduled": {"date": "2026-10-14"}, "scope_status": "explicit",
                "covered_topics": ["Reverse a singly linked list"], "source_refs": []}]


class PlanCourseTests(unittest.TestCase):
    def test_assembles_contract_lesson_requests(self):
        lessons = [{
            "unit_title": "Linked lists", "objective_title": "Reverse a singly linked list",
            "learning_goal": "iteratively reverse pointers", "importance": "core",
            "is_suggested_practice": False, "exam_related": True, "prerequisite_titles": [],
            "suggested_formats": ["visual_explainer"], "teaching_approaches": ["pointer_trace"],
            "target_duration_seconds": 45,
        }]
        plan = plan_course(COURSE, UNITS, ASSESSMENTS, client(lessons))
        self.assertEqual(len(plan["requests"]), 1)
        lr = plan["requests"][0]
        self.assertEqual(lr["scope"], "private")
        self.assertEqual(lr["importance"], "core")
        self.assertEqual(lr["evidence_status"], "explicit")  # has source refs, not practice
        self.assertEqual(lr["exam_scope_status"], "explicit")  # exam-related + explicit assessment
        self.assertEqual(lr["source_refs"], ["src_canvas_c1_syllabus"])
        self.assertIn("a1", lr["assessment_ids"])
        self.assertEqual(lr["desired_variant_count"], 2)

    def test_suggested_practice_never_exam_scope(self):
        lessons = [{
            "unit_title": "Linked lists", "objective_title": "Cycle detection",
            "learning_goal": "fast/slow pointers", "importance": "optional",
            "is_suggested_practice": True, "exam_related": True,  # model wrongly says exam
            "prerequisite_titles": [], "suggested_formats": ["worked_example"],
            "teaching_approaches": [], "target_duration_seconds": 50,
        }]
        lr = plan_course(COURSE, UNITS, ASSESSMENTS, client(lessons))["requests"][0]
        self.assertEqual(lr["evidence_status"], "suggested_practice")
        self.assertEqual(lr["exam_scope_status"], "unknown")  # practice can't be exam scope
        self.assertEqual(lr["assessment_ids"], [])

    def test_duration_clamped_and_bad_format_dropped(self):
        lessons = [{
            "unit_title": "Linked lists", "objective_title": "Traversal",
            "learning_goal": "walk a list", "importance": "weird",
            "is_suggested_practice": False, "exam_related": False, "prerequisite_titles": [],
            "suggested_formats": ["not_a_format"], "teaching_approaches": [],
            "target_duration_seconds": 300,
        }]
        lr = plan_course(COURSE, UNITS, ASSESSMENTS, client(lessons))["requests"][0]
        self.assertEqual(lr["target_duration_seconds"], 60)   # clamped
        self.assertEqual(lr["suggested_formats"], ["visual_explainer"])  # fallback
        self.assertEqual(lr["importance"], "supporting")  # bad enum -> default

    def test_prerequisites_link_within_course(self):
        lessons = [
            {"unit_title": "Linked lists", "objective_title": "Nodes and pointers",
             "learning_goal": "g", "importance": "core", "is_suggested_practice": False,
             "exam_related": False, "prerequisite_titles": [], "suggested_formats": [],
             "teaching_approaches": [], "target_duration_seconds": 40},
            {"unit_title": "Linked lists", "objective_title": "Reverse a list",
             "learning_goal": "g", "importance": "core", "is_suggested_practice": False,
             "exam_related": False, "prerequisite_titles": ["Nodes and pointers"],
             "suggested_formats": [], "teaching_approaches": [], "target_duration_seconds": 40},
        ]
        reqs = plan_course(COURSE, UNITS, ASSESSMENTS, client(lessons))["requests"]
        base_oid = reqs[0]["objective_id"]
        self.assertEqual(reqs[1]["prerequisite_objective_ids"], [base_oid])

    def test_build_lesson_plans_skips_non_ready(self):
        profile = {
            "profile_id": "p1", "revision": 1, "user_id": "u1",
            "courses": [COURSE, {"course_id": "c2", "import_status": "needs_review"}],
            "units": UNITS, "assessments": ASSESSMENTS,
        }
        lessons = [{"unit_title": "Linked lists", "objective_title": "X", "learning_goal": "g",
                    "importance": "core", "is_suggested_practice": False, "exam_related": False,
                    "prerequisite_titles": [], "suggested_formats": [], "teaching_approaches": [],
                    "target_duration_seconds": 40}]
        plans = build_lesson_plans(profile, client(lessons))
        self.assertEqual(len(plans), 1)  # only the ready course
        self.assertEqual(plans[0]["course_id"], "c1")
        self.assertEqual(plans[0]["profile_id"], "p1")


if __name__ == "__main__":
    unittest.main()


class TimelinePlanningTests(unittest.TestCase):
    def test_only_verified_current_exam_topics_are_planned(self):
        from datetime import datetime, timezone

        from app.modules.curriculum.timing import priority_targets

        def assessment(identifier, day, topic, status="explicit"):
            return {
                "assessment_id": identifier, "title": identifier, "kind": "midterm",
                "scheduled": {"date": day, "precision": "date", "evidence_status": status,
                              "timezone": "America/New_York"},
                "scope_status": "explicit", "covered_topics": [topic],
            }

        course = {**COURSE, "external_course_id": "sample"}
        old = assessment("past", "2026-09-15", "earlier topic")
        current = assessment("current", "2026-11-14", "line integrals")
        unknown = assessment("undated", None, "vector fields", "unknown")
        tests = [old, current, unknown]
        now = datetime(2026, 11, 15, 2, tzinfo=timezone.utc)
        proposals = [
            {"objective_title": topic, "learning_goal": f"Practice {topic}",
             "target_assessment_id": target, "target_topic": topic}
            for target, topic in [
                ("past", "earlier topic"),
                ("current", "earlier topic"),
                ("undated", "vector fields"),
                ("current", "line integrals"),
            ]
        ]
        requests = plan_course(course, UNITS, tests, client(proposals), now=now)["requests"]
        self.assertEqual([request["title"] for request in requests], ["line integrals"])
        self.assertEqual(requests[0]["assessment_ids"], ["current"])
        self.assertEqual(requests[0]["exam_scope_status"], "explicit")
        # An older topic becomes relevant again when the current exam lists it.
        current["covered_topics"].append("earlier topic")
        requests = plan_course(course, UNITS, tests, client(proposals), now=now)["requests"]
        self.assertEqual({request["title"] for request in requests}, {"earlier topic", "line integrals"})
        self.assertEqual(priority_targets(tests, now.replace(hour=6)), [])
        self.assertEqual(plan_course(course, UNITS, tests, None,
                                     now=now.replace(hour=6))["requests"], [])

    def test_numbered_homework_does_not_supply_a_topic(self):
        from app.modules.curriculum.timing import target_topic_is_supported

        assignment = {"kind": "assignment", "title": "HW 16.1"}
        self.assertFalse(target_topic_is_supported("HW 16.1", assignment))
        self.assertFalse(target_topic_is_supported("Lagrange multipliers", assignment))
        assignment["title"] = "HW 16.1: Lagrange multipliers"
        self.assertTrue(target_topic_is_supported("Lagrange multipliers", assignment))
