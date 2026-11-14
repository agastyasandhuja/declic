import json
import unittest

from app.modules.canvas.client.http import CanvasClient, Response
from app.modules.canvas.config import Secret
from app.modules.canvas.courses import summarize_current_courses

ORIGIN = "https://canvas.example.edu"


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def __call__(self, url, headers, timeout):
        self.urls.append(url)
        return self.responses.pop(0)


def ok(payload):
    return Response(200, {}, json.dumps(payload).encode())


def client(transport):
    return CanvasClient(ORIGIN, Secret("t"), transport=transport, sleep=lambda _: None)


class CourseSummaryTests(unittest.TestCase):
    def test_normalizes_fields_and_strips_syllabus_html(self):
        transport = FakeTransport(
            [
                ok(
                    [
                        {
                            "id": 101,
                            "name": "Data Structures",
                            "time_zone": "America/New_York",
                            "term": {"name": "Fall 2026"},
                            "syllabus_body": "<p>Units: <b>linked lists</b></p>",
                        }
                    ]
                )
            ]
        )
        [course] = summarize_current_courses(client(transport))
        self.assertEqual(course.external_course_id, "101")
        self.assertEqual(course.title, "Data Structures")
        self.assertEqual(course.term, "Fall 2026")
        self.assertIn("linked lists", course.syllabus_preview)
        self.assertNotIn("<", course.syllabus_preview)
        self.assertEqual(course.missing, [])
        # request asks Canvas for the student's own active enrollments + syllabus
        self.assertIn("enrollment_type=student", transport.urls[0])
        self.assertIn("syllabus_body", transport.urls[0])

    def test_missing_syllabus_is_recorded_not_fatal(self):
        transport = FakeTransport(
            [ok([{"id": 102, "name": "Accounting", "syllabus_body": None}])]
        )
        [course] = summarize_current_courses(client(transport))
        self.assertEqual(course.syllabus_chars, 0)
        self.assertEqual(course.missing, ["syllabus"])
        self.assertEqual(course.term, "unknown")
        self.assertEqual(course.timezone, "unknown")

    def test_skips_malformed_entries(self):
        transport = FakeTransport([ok([{"name": "no id"}, "garbage", {"id": 5, "name": "Ok"}])])
        courses = summarize_current_courses(client(transport))
        self.assertEqual([c.external_course_id for c in courses], ["5"])


if __name__ == "__main__":
    unittest.main()
