import json
import tempfile
import unittest
from pathlib import Path

from app.modules.canvas.ingestion.uploads import store_upload
from app.modules.curriculum.client.gemini import GeminiClient, GeminiError, parse_json_object
from app.modules.curriculum.config import GeminiConfigError, GeminiSettings, Secret
from app.modules.curriculum.extract import build_profile
from app.modules.curriculum.schemas import EXTRACTION_SCHEMA
from app.modules.curriculum.sources import CanvasSourceResolver, ResolvedSource, SourceResolver
from app.modules.curriculum.validators import validate_extraction


class StaticResolver:
    """A simple in-memory resolver for pipeline tests (no Canvas, no uploads)."""

    def __init__(self, sources):
        self._sources = sources

    def list_sources(self):
        return self._sources

    def sources_for_course(self, course_id):
        return [s for s in self._sources if s.course_id == course_id]

    def course_ids(self):
        out = []
        for s in self._sources:
            if s.course_id not in out:
                out.append(s.course_id)
        return out


def _source(course_id, text, sid=None):
    return ResolvedSource(
        source_id=sid or f"src_{course_id}", course_id=course_id, title=f"{course_id} syllabus",
        resource_type="canvas_syllabus", provenance_mode="canvas", text=text,
    )

SYLLABUS = (
    "Course: Demo DSA\nTerm: Fall 2026\nTime zone: America/New_York\n"
    "Unit 2 Linked lists: reversal.\nMidterm 1 on 2026-10-14 covers linked lists.\n"
)


def settings():
    return GeminiSettings.from_env({"GEMINI_API_KEY": "synthetic-key", "GEMINI_MODEL": "demo-flash"})


def gemini_response(obj: dict, status: int = 200) -> tuple[int, bytes]:
    body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(obj)}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}}
    return status, json.dumps(body).encode()


class ConfigTests(unittest.TestCase):
    def test_requires_key_and_model(self):
        with self.assertRaises(GeminiConfigError):
            GeminiSettings.from_env({"GEMINI_MODEL": "x"})
        with self.assertRaises(GeminiConfigError):
            GeminiSettings.from_env({"GEMINI_API_KEY": "k"})

    def test_key_is_wrapped(self):
        s = settings()
        self.assertNotIn("synthetic-key", repr(s))
        self.assertEqual(s.api_key.reveal(), "synthetic-key")


class ClientTests(unittest.TestCase):
    def test_generate_json_sends_schema_and_key_header(self):
        captured = {}

        def transport(url, body, headers):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json.loads(body)
            return gemini_response({"course_title": "Demo"})

        client = GeminiClient(settings(), transport=transport)
        result = client.generate_json(system_instruction="sys", user_content="hi", response_schema=EXTRACTION_SCHEMA)
        self.assertIn(":generateContent", captured["url"])
        self.assertEqual(captured["headers"]["x-goog-api-key"], "synthetic-key")
        self.assertEqual(captured["body"]["generationConfig"]["responseMimeType"], "application/json")
        self.assertIn("Demo", result.text)

    def test_error_status_has_no_key(self):
        def transport(url, body, headers):
            return 403, json.dumps({"error": {"message": "key disabled"}}).encode()

        with self.assertRaises(GeminiError) as ctx:
            GeminiClient(settings(), transport=transport).generate_json(
                system_instruction="s", user_content="u", response_schema=EXTRACTION_SCHEMA
            )
        self.assertNotIn("synthetic-key", str(ctx.exception))
        self.assertEqual(ctx.exception.status, 403)

    def test_parse_json_tolerates_code_fence(self):
        self.assertEqual(parse_json_object('```json\n{"a": 1}\n```'), {"a": 1})
        with self.assertRaises(GeminiError):
            parse_json_object("not json")


class ValidatorTests(unittest.TestCase):
    def test_drops_unauthorized_source_ids(self):
        raw = {"course_title": "C", "term": None, "timezone": "America/New_York",
               "units": [{"title": "U", "order": 1, "objectives": ["o"], "source_ids": ["ok", "FAKE"]}],
               "assessments": [], "textbooks": [], "warnings": []}
        clean = validate_extraction(raw, {"ok"})
        self.assertEqual(clean["units"][0]["source_refs"], ["ok"])
        self.assertTrue(any("not authorized" in w for w in clean["warnings"]))

    def test_never_manufactures_exam_time(self):
        raw = {"course_title": "C", "term": None, "timezone": "America/New_York",
               "units": [], "textbooks": [], "warnings": [],
               "assessments": [{"title": "Final", "kind": "final", "date": None, "time": "09:00",
                                "date_evidence": "inferred", "scope_status": "unknown",
                                "covered_topics": [], "source_ids": []}]}
        clean = validate_extraction(raw, set())
        when = clean["assessments"][0]["scheduled"]
        self.assertIsNone(when["timestamp"])
        self.assertIsNone(when["date"])
        self.assertEqual(when["precision"], "unknown")

    def test_date_only_keeps_precision_date_no_timestamp(self):
        raw = {"course_title": "C", "term": None, "timezone": "America/New_York",
               "units": [], "textbooks": [], "warnings": [],
               "assessments": [{"title": "Midterm", "kind": "midterm", "date": "2026-10-14", "time": None,
                                "date_evidence": "explicit", "scope_status": "explicit",
                                "covered_topics": ["linked lists"], "source_ids": []}]}
        when = validate_extraction(raw, set())["assessments"][0]["scheduled"]
        self.assertEqual(when["date"], "2026-10-14")
        self.assertIsNone(when["timestamp"])
        self.assertEqual(when["precision"], "date")

    def test_conflicting_dates_warn(self):
        raw = {"course_title": "C", "term": None, "timezone": None, "units": [], "textbooks": [], "warnings": [],
               "assessments": [
                   {"title": "Midterm", "kind": "midterm", "date": "2026-10-14", "time": None,
                    "date_evidence": "explicit", "scope_status": "explicit", "covered_topics": [], "source_ids": []},
                   {"title": "midterm", "kind": "midterm", "date": "2026-10-20", "time": None,
                    "date_evidence": "explicit", "scope_status": "explicit", "covered_topics": [], "source_ids": []}]}
        clean = validate_extraction(raw, set())
        self.assertTrue(any("conflicting dates" in w for w in clean["warnings"]))

    def test_bad_enum_coerced(self):
        raw = {"course_title": "C", "term": None, "timezone": None, "units": [], "textbooks": [], "warnings": [],
               "assessments": [{"title": "X", "kind": "pop-quiz", "date": None, "time": None,
                                "date_evidence": "maybe", "scope_status": "sure",
                                "covered_topics": [], "source_ids": []}]}
        a = validate_extraction(raw, set())["assessments"][0]
        self.assertEqual(a["kind"], "other")
        self.assertEqual(a["scope_status"], "unknown")


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)

    def _client(self, responder):
        return GeminiClient(settings(), transport=responder)

    def test_build_profile_end_to_end_with_fake_gemini(self):
        resolver = StaticResolver([_source("c1", SYLLABUS)])

        def responder(url, body, headers):
            # echo a plausible extraction; source_ids left empty (safe)
            return gemini_response({
                "course_title": "Demo DSA", "term": "Fall 2026", "timezone": "America/New_York",
                "units": [{"title": "Linked lists", "order": 2, "objectives": ["reverse a list"], "source_ids": []}],
                "assessments": [{"title": "Midterm 1", "kind": "midterm", "date": "2026-10-14", "time": None,
                                 "date_evidence": "explicit", "scope_status": "explicit",
                                 "covered_topics": ["linked lists"], "source_ids": []}],
                "textbooks": [], "warnings": []})

        profile = build_profile("u1", resolver, self._client(responder), self.dir, persist=True)
        self.assertEqual(profile["revision"], 1)
        self.assertEqual(len(profile["courses"]), 1)
        self.assertEqual(profile["courses"][0]["import_status"], "ready")
        self.assertEqual(profile["units"][0]["title"], "Linked lists")
        self.assertEqual(profile["assessments"][0]["scheduled"]["date"], "2026-10-14")
        # second build increments revision
        profile2 = build_profile("u1", resolver, self._client(responder), self.dir, persist=True)
        self.assertEqual(profile2["revision"], 2)

    def test_authorized_source_ids_only(self):
        # Gemini citing a source id outside the authorized set gets it dropped.
        resolver = StaticResolver([_source("c1", SYLLABUS, sid="src_canvas_c1_syllabus")])

        def responder(url, body, headers):
            return gemini_response({
                "course_title": "DSA", "term": None, "timezone": None,
                "units": [{"title": "U", "order": 1, "objectives": ["o"],
                           "source_ids": ["src_canvas_c1_syllabus", "src_made_up"]}],
                "assessments": [], "textbooks": [], "warnings": []})

        profile = build_profile("u1", resolver, self._client(responder), self.dir, persist=False)
        self.assertEqual(profile["units"][0]["source_refs"], ["src_canvas_c1_syllabus"])

    def test_one_course_failure_does_not_abort(self):
        resolver = StaticResolver([_source("c1", SYLLABUS), _source("c2", "Unit 1 counting.")])
        calls = {"n": 0}

        def responder(url, body, headers):
            calls["n"] += 1
            if calls["n"] == 1:
                return 500, b'{"error":{"message":"boom"}}'
            return gemini_response({"course_title": "Ok", "term": None, "timezone": None,
                                    "units": [], "assessments": [], "textbooks": [], "warnings": []})

        profile = build_profile("u1", resolver, self._client(responder), self.dir, persist=False)
        statuses = {c["import_status"] for c in profile["courses"]}
        self.assertIn("error", statuses)
        self.assertIn("ready", statuses)

    def test_course_without_syllabus_needs_review_not_fatal(self):
        resolver = StaticResolver([_source("c1", None)])  # no extractable text
        profile = build_profile("u1", resolver, self._client(lambda *a: gemini_response({})), self.dir, persist=False)
        self.assertEqual(profile["courses"][0]["import_status"], "needs_review")

    def test_no_sources_raises(self):
        with self.assertRaises(ValueError):
            build_profile("u1", StaticResolver([]), self._client(lambda *a: gemini_response({})), self.dir, persist=False)


class CanvasResolverTests(unittest.TestCase):
    def test_turns_live_courses_into_authorized_sources(self):
        import json as _json

        from app.modules.canvas.client.http import CanvasClient, Response
        from app.modules.canvas.config import Secret as CanvasSecret

        courses = [
            {"id": 101, "name": "DSA", "syllabus_body": "<p>Unit 2 linked lists</p>"},
            {"id": 102, "name": "Accounting", "syllabus_body": None},
        ]

        def transport(url, headers, timeout):
            return Response(200, {}, _json.dumps(courses).encode())

        canvas = CanvasClient("https://canvas.example.edu", CanvasSecret("t"),
                              transport=transport, sleep=lambda _: None)
        resolver = CanvasSourceResolver(canvas, with_assignments=False)  # syllabus only here
        self.assertEqual(resolver.course_ids(), ["101", "102"])
        dsa = resolver.sources_for_course("101")[0]
        self.assertEqual(dsa.source_id, "src_canvas_101_overview")
        self.assertIn("linked lists", dsa.text)
        self.assertIsNone(resolver.sources_for_course("102")[0].text)


if __name__ == "__main__":
    unittest.main()
