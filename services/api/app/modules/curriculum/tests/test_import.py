"""Regression tests using synthetic Canvas and Gemini data."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from app.modules.canvas.client.http import CanvasClient, Response
from app.modules.canvas.config import Secret
from app.modules.canvas.ingestion.resources import _file_text
from app.modules.curriculum.client.gemini import GeminiClient
from app.modules.curriculum.corrections import RevisionConflict
from app.modules.curriculum.service import AcademicService
from app.modules.curriculum.sources import CanvasSourceResolver
from app.modules.curriculum.tests.test_curriculum import gemini_response, settings


class AcademicImportTests(unittest.TestCase):
    def test_inventory_grounding_scope_and_reimport(self):
        repo = Path(__file__).resolve().parents[6]
        inventory = json.loads((repo / "fixtures/academics/canvas_resources.json").read_text())

        def canvas(url, headers, timeout):
            parsed = urlsplit(url)
            self.assertEqual(parsed.hostname, "canvas.example")
            if parsed.path == "/files/8/download":
                return Response(200, {}, b"Iterative reversal traces three pointer updates.")
            if parsed.path == "/api/v1/calendar_events":
                self.assertEqual(parse_qs(parsed.query)["context_codes[]"], ["course_17"])
            self.assertIn(parsed.path, inventory)
            return Response(200, {}, json.dumps(inventory[parsed.path]).encode())

        client = CanvasClient("https://canvas.example", Secret("fake-token"), transport=canvas)
        resolver = CanvasSourceResolver(client, owner_user_id="owner")
        sources = {source.resource_type: source for source in resolver.list_sources() if source.has_text}
        page, event = sources["page"], sources["calendar_event"]
        self.assertNotIn("hidden script", page.text)
        self.assertNotIn("Unrelated calendar event", event.text)
        self.assertTrue(sources["file"].content_hash)
        self.assertIn("file: some excerpts unavailable", resolver.course_info("17")["missing_sources"])

        def gemini(url, body, headers):
            prompt = str(body)
            self.assertIn("Save the next pointer", prompt)
            self.assertNotIn("fake-token", prompt)
            if "Allowed suggested_formats" in prompt:
                return gemini_response({"lessons": [{
                    "objective_title": "Reverse a list", "learning_goal": "Trace pointer updates",
                    "unit_title": "Pointers", "target_duration_seconds": 45,
                }]})
            return gemini_response({
                "course_title": "Synthetic Data Structures",
                "units": [{"title": "Pointers", "source_ids": [page.source_id]}],
                "assessments": [
                    {"title": "Midterm 1", "date": "2026-11-19", "time": "09:00",
                     "source_ids": [event.source_id], "date_evidence": "explicit"},
                    {"title": "Final Exam", "date": "2026-11-19", "source_ids": [event.source_id]},
                ],
            })

        with tempfile.TemporaryDirectory() as folder:
            service = AcademicService(Path(folder), GeminiClient(settings(), transport=gemini))
            with self.assertRaises(PermissionError):
                service.import_profile("other", resolver)
            profile = service.import_profile("owner", resolver)
            midterm, final = profile["assessments"]
            self.assertEqual(midterm["scheduled"]["precision"], "date")
            self.assertIsNone(final["scheduled"]["date"])
            self.assertEqual(len(service.get_validated_plans("owner")), 1)
            self.assertEqual(service.get_validated_plans("other"), [])
            self.assertEqual(service.get_course_bindings("owner")[0]["source_refs"], [page.source_id])
            self.assertEqual(service.resolve_source_context("owner", [page.source_id])[0]["text"], page.text)
            with self.assertRaises(LookupError):
                service.resolve_source_context("other", [page.source_id])
            with self.assertRaises(LookupError):
                service.resolve_source_context("owner", [{"source_id": page.source_id, "course_id": "18"}])
            service.apply_corrections("owner", 1, [{"assessment_id": midterm["assessment_id"], "date": None}])
            self.assertEqual(service.get_validated_plans("owner"), [])
            with self.assertRaises(RevisionConflict):
                service.apply_corrections("owner", 1, [{"assessment_id": midterm["assessment_id"], "date": None}])
            imported = service.import_profile("owner", CanvasSourceResolver(client))
            self.assertEqual(imported["revision"], 3)
            self.assertIsNone(imported["assessments"][0]["scheduled"]["date"])
            self.assertEqual(imported["assessments"][0]["scheduled"]["evidence_status"], "user_confirmed")

    def test_pptx_extracts_slide_text(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("ppt/slides/slide2.xml",
                             '<a:t xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">Pointers</a:t>')
        self.assertEqual(_file_text(".pptx", output.getvalue()), "Slide 2: Pointers")
