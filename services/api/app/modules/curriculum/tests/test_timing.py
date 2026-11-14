import json
import unittest
from datetime import datetime, timezone

from app.modules.canvas.assignments import Assignment, fetch_assignments
from app.modules.canvas.client.http import CanvasClient, Response
from app.modules.canvas.config import Secret
from app.modules.curriculum.timing import course_timing, schedule_text

NOW = datetime(2026, 11, 14, tzinfo=timezone.utc)


def a(name, due, exam_points=None):
    return Assignment(external_id=name, name=name, due_at=due, points_possible=exam_points)


class TimingTests(unittest.TestCase):
    def test_nearest_upcoming_and_urgency(self):
        items = [
            a("Quiz 8", "2026-11-18T03:59:59Z"),
            a("HW 5", "2026-11-24T03:59:59Z"),
            a("Old HW", "2026-10-01T03:59:59Z"),  # past, ignored for "next"
        ]
        t = course_timing(items, now=NOW)
        self.assertEqual(t.next_due_name, "Quiz 8")
        self.assertEqual(t.next_due_date, "2026-11-18")
        self.assertEqual(t.days_until_next, 4)
        self.assertEqual(t.upcoming_count, 2)
        self.assertGreater(t.urgency, 0.8)  # 4 days out -> very urgent

    def test_no_upcoming_scores_zero(self):
        t = course_timing([a("Old", "2026-09-01T03:59:59Z")], now=NOW)
        self.assertIsNone(t.days_until_next)
        self.assertEqual(t.urgency, 0.0)

    def test_undated_exam_detected_not_guessed(self):
        t = course_timing([a("Midterm 1", None)], now=NOW)
        self.assertTrue(t.has_undated_exam)
        self.assertIsNone(t.next_due_date)   # never invents a date
        self.assertIsNone(t.next_exam_days)

    def test_dated_exam_tracked(self):
        t = course_timing([a("Final Exam", "2026-12-15T15:00:00Z")], now=NOW)
        self.assertEqual(t.next_exam_days, 31)

    def test_sooner_course_is_more_urgent(self):
        soon = course_timing([a("Q", "2026-11-16T00:00:00Z")], now=NOW).urgency
        later = course_timing([a("Q", "2026-12-20T00:00:00Z")], now=NOW).urgency
        self.assertGreater(soon, later)

    def test_schedule_text_marks_past_and_upcoming_no_invention(self):
        text = schedule_text([a("Quiz 8", "2026-11-18T03:59:59Z"),
                              a("Old HW", "2026-10-01T03:59:59Z"),
                              a("Midterm 1", None)], now=NOW)
        self.assertIn("upcoming): Quiz 8", text)
        self.assertIn("past): Old HW", text)
        self.assertIn("without a date", text)


class AssignmentFetchTests(unittest.TestCase):
    def test_fetch_parses_and_flags_exams(self):
        payload = [
            {"id": 1, "name": "Quiz 8", "due_at": "2026-11-18T03:59:59Z", "points_possible": 10},
            {"id": 2, "name": "Midterm 1", "due_at": None},
            {"garbage": True},
        ]
        transport = lambda url, headers, timeout: Response(200, {}, json.dumps(payload).encode())
        client = CanvasClient("https://c.edu", Secret("t"), transport=transport, sleep=lambda _: None)
        items = fetch_assignments(client, "39039")
        self.assertEqual(len(items), 2)
        self.assertFalse(items[0].looks_like_exam)
        self.assertTrue(items[1].looks_like_exam)
        self.assertIsNone(items[1].due_at)


if __name__ == "__main__":
    unittest.main()
