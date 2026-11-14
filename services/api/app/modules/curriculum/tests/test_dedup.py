"""Reimport dedup: a course whose sources are unchanged reuses its prior
extraction instead of calling Gemini again; a changed source re-extracts."""
import json
import tempfile
import unittest
from pathlib import Path

from app.modules.curriculum.client.gemini import GeminiClient
from app.modules.curriculum.config import GeminiSettings
from app.modules.curriculum.extract import build_profile
from app.modules.curriculum.sources import ResolvedSource


def settings():
    return GeminiSettings.from_env({"GEMINI_API_KEY": "k", "GEMINI_MODEL": "m"})


class CountingResolver:
    """Static resolver whose one source's stamp (content_hash) we can change."""
    def __init__(self, stamp):
        self.stamp = stamp

    def _sources(self):
        return [ResolvedSource("src_c1_overview", "c1", "DSA syllabus", "canvas_course",
                               "canvas", "Unit 1 linked lists. Midterm 1.", "e1",
                               content_hash=self.stamp)]

    def list_sources(self):
        return self._sources()

    def sources_for_course(self, course_id):
        return [s for s in self._sources() if s.course_id == course_id]

    def course_ids(self):
        return ["c1"]


def gemini(calls):
    def transport(url, body, headers):
        calls.append(1)
        payload = {"course_title": "DSA", "term": "Fall 2026", "timezone": "America/New_York",
                   "units": [{"title": "Linked lists", "order": 1, "objectives": ["reversal"], "source_ids": []}],
                   "assessments": [], "textbooks": [], "warnings": []}
        body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(payload)}]}}],
                "usageMetadata": {}}
        return 200, json.dumps(body).encode()
    return GeminiClient(settings(), transport=transport)


class DedupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)

    def test_unchanged_sources_reuse_prior_extraction(self):
        calls = []
        resolver = CountingResolver(stamp="hash-v1")
        p1 = build_profile("u1", resolver, gemini(calls), self.dir, persist=True)
        self.assertEqual(len(calls), 1)  # Gemini called once
        self.assertTrue(p1["courses"][0]["sources_fingerprint"])

        # Reimport with identical sources: no new Gemini call, result reused.
        p2 = build_profile("u1", CountingResolver(stamp="hash-v1"), gemini(calls), self.dir, persist=True)
        self.assertEqual(len(calls), 1)  # still 1 — reused
        self.assertTrue(any("reused unchanged" in w for w in p2["warnings"]))
        self.assertEqual(p2["units"][0]["title"], "Linked lists")

    def test_changed_source_triggers_reextraction(self):
        calls = []
        build_profile("u1", CountingResolver(stamp="hash-v1"), gemini(calls), self.dir, persist=True)
        self.assertEqual(len(calls), 1)
        # A changed content hash -> different fingerprint -> re-extract.
        build_profile("u1", CountingResolver(stamp="hash-v2"), gemini(calls), self.dir, persist=True)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
