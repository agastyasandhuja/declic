import json
import tempfile
import unittest
from pathlib import Path

from app.modules.canvas.client.http import (
    CanvasAuthError,
    CanvasClient,
    CanvasError,
    CanvasUnavailable,
    Response,
)
from app.modules.canvas.config import CanvasConfigError, CanvasSettings, Secret
from app.modules.canvas.ingestion.uploads import UploadRejected, store_upload

ORIGIN = "https://canvas.example.edu"
TOKEN = "synthetic-token-not-real"


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers)))
        return self.responses.pop(0)


def ok(payload, link=None):
    headers = {"link": link} if link else {}
    return Response(200, headers, json.dumps(payload).encode())


def client(transport, **kwargs):
    return CanvasClient(
        ORIGIN, Secret(TOKEN), transport=transport, sleep=lambda _: None, **kwargs
    )


class ConfigTests(unittest.TestCase):
    def test_rejects_http_and_paths(self):
        for bad in ("http://canvas.example.edu", f"{ORIGIN}/api/v1", "https://u:p@x.edu"):
            with self.assertRaises(CanvasConfigError):
                CanvasSettings.from_env({"CANVAS_BASE_URL": bad})

    def test_token_requires_bound_user(self):
        with self.assertRaises(CanvasConfigError):
            CanvasSettings.from_env({"CANVAS_BASE_URL": ORIGIN, "CANVAS_DEV_TOKEN": TOKEN})

    def test_token_only_for_bound_user_and_never_in_repr(self):
        settings = CanvasSettings.from_env(
            {
                "CANVAS_BASE_URL": ORIGIN + "/",
                "CANVAS_DEV_TOKEN": TOKEN,
                "CANVAS_DEV_TOKEN_APP_USER_ID": "user-a",
            }
        )
        self.assertEqual(settings.institution_origin, ORIGIN)
        self.assertEqual(settings.available_modes(), ["developer_token", "upload"])
        self.assertEqual(settings.developer_token_for("user-a").reveal(), TOKEN)
        with self.assertRaises(PermissionError):
            settings.developer_token_for("user-b")
        self.assertNotIn(TOKEN, repr(settings))
        self.assertNotIn(TOKEN, f"{settings.dev_token}")

    def test_upload_is_only_mode_without_credentials(self):
        settings = CanvasSettings.from_env({"CANVAS_BASE_URL": ORIGIN})
        self.assertEqual(settings.available_modes(), ["upload"])


class ClientTests(unittest.TestCase):
    def test_paginates_via_link_header(self):
        nxt = f'<{ORIGIN}/api/v1/courses?page=2&per_page=50>; rel="next"'
        transport = FakeTransport([ok([{"id": 1}], nxt), ok([{"id": 2}])])
        items = list(client(transport).paginate("/api/v1/courses"))
        self.assertEqual([i["id"] for i in items], [1, 2])
        self.assertEqual(transport.calls[0][1]["Authorization"], f"Bearer {TOKEN}")

    def test_refuses_next_link_on_other_host(self):
        nxt = '<https://evil.example.com/api/v1/courses?page=2>; rel="next"'
        transport = FakeTransport([ok([{"id": 1}], nxt)])
        with self.assertRaises(CanvasError):
            list(client(transport).paginate("/api/v1/courses"))
        self.assertEqual(len(transport.calls), 1)  # token never sent to the other host

    def test_page_cap(self):
        nxt = f'<{ORIGIN}/api/v1/courses?page=2>; rel="next"'
        transport = FakeTransport([ok([1], nxt), ok([2], nxt)])
        with self.assertRaises(CanvasError):
            list(client(transport, max_pages=2).paginate("/api/v1/courses"))

    def test_error_mapping_without_token_leak(self):
        cases = [(401, CanvasAuthError), (403, CanvasUnavailable), (404, CanvasUnavailable)]
        for status, expected in cases:
            transport = FakeTransport([Response(status, {}, b"{}")])
            with self.assertRaises(expected) as ctx:
                client(transport).get("/api/v1/users/self", [("secret_q", "v")])
            self.assertNotIn(TOKEN, str(ctx.exception))
            self.assertNotIn("secret_q", str(ctx.exception))

    def test_cross_origin_redirect_is_an_error(self):
        transport = FakeTransport([Response(302, {"location": "https://cdn.example.com/x"}, b"")])
        with self.assertRaises(CanvasError):
            client(transport).get("/api/v1/users/self")

    def test_retries_throttle_then_succeeds(self):
        transport = FakeTransport(
            [
                Response(403, {}, b"403 Forbidden (Rate Limit Exceeded)"),
                Response(503, {"retry-after": "1"}, b""),
                ok({"id": 7}),
            ]
        )
        self.assertEqual(client(transport).get("/api/v1/users/self"), {"id": 7})

    def test_retries_are_bounded(self):
        transport = FakeTransport([Response(503, {}, b"")] * 3)
        with self.assertRaises(CanvasError):
            client(transport).get("/api/v1/users/self")
        self.assertEqual(len(transport.calls), 3)

    def test_only_api_paths_and_no_write_methods(self):
        with self.assertRaises(CanvasError):
            client(FakeTransport([])).get("/login/oauth2/token")
        for verb in ("post", "put", "patch", "delete"):
            self.assertFalse(hasattr(CanvasClient, verb))

    def test_malformed_json(self):
        transport = FakeTransport([Response(200, {}, b"<html>login</html>")])
        with self.assertRaises(CanvasError):
            client(transport).get("/api/v1/users/self")


class UploadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)

    def store(self, filename="syllabus.pdf", data=b"%PDF-1.7 synthetic", user="user-a", course="Synthetic DSA"):
        return store_upload(
            user_id=user, course_label=course, filename=filename, data=data, storage_dir=self.dir
        )

    def test_stores_private_record_with_demo_provenance(self):
        record, created = self.store()
        self.assertTrue(created)
        self.assertEqual(record["scope"], "private")
        self.assertEqual(record["resource_type"], "upload")
        self.assertEqual(record["provenance"]["mode"], "upload")
        self.assertTrue(record["provenance"]["demo"])
        self.assertTrue(record["fetched_at"].endswith("+00:00"))

    def test_identical_reupload_is_reused(self):
        first, _ = self.store()
        second, created = self.store(course="  synthetic   dsa ")
        self.assertFalse(created)
        self.assertEqual(first["source_id"], second["source_id"])

    def test_users_and_courses_are_separate(self):
        a, _ = self.store()
        b, _ = self.store(user="user-b")
        c, _ = self.store(course="Synthetic Probability")
        self.assertEqual(len({a["source_id"], b["source_id"], c["source_id"]}), 3)
        self.assertNotEqual(a["storage_ref"], b["storage_ref"])

    def test_rejections(self):
        bad = [
            dict(filename="run.exe"),
            dict(filename="fake.pdf", data=b"MZ not a pdf"),
            dict(filename="notes.txt", data=b"\xff\xfe\x00binary"),
            dict(data=b""),
            dict(course="   "),
            dict(user=""),
        ]
        for kwargs in bad:
            with self.assertRaises(UploadRejected):
                self.store(**kwargs)

    def test_filename_cannot_escape_storage(self):
        record, _ = self.store(filename="../../etc/evil.pdf")
        self.assertEqual(record["title"], "evil.pdf")
        stored = [p for p in self.dir.rglob("*") if p.is_file()]
        self.assertTrue(all(self.dir in p.resolve().parents for p in stored))


if __name__ == "__main__":
    unittest.main()
