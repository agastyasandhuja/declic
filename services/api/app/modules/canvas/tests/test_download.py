"""Tests for the file-download path: it must follow Canvas's redirect to its
file/CDN host while never sending the bearer token off the institution origin,
and refuse hosts that are not Canvas file hosts."""
import unittest

from app.modules.canvas.client.http import (
    CanvasClient, CanvasError, Response, _file_host_allowed,
)
from app.modules.canvas.config import Secret

ORIGIN = "https://school.instructure.com"
TOKEN = "secret-token-not-real"


class HostAllowlistTests(unittest.TestCase):
    def test_allows_institution_and_canvas_file_hosts(self):
        for url in [
            f"{ORIGIN}/files/1/download",
            "https://x-1.cluster1.canvas-user-content.com/files/1?verifier=y",
            "https://inst-fs-iad-prod.inscloudgate.net/files/abc",
            "https://instructure-uploads.s3.amazonaws.com/x",
        ]:
            self.assertTrue(_file_host_allowed(url, ORIGIN), url)

    def test_rejects_foreign_and_insecure_hosts(self):
        for url in [
            "https://evil.com/files/1",
            "https://notinstructure.com/x",
            "http://school.instructure.com/files/1",  # not https
            "https://instructure.com.evil.com/x",
        ]:
            self.assertFalse(_file_host_allowed(url, ORIGIN), url)


class DownloadTokenTests(unittest.TestCase):
    def _client(self, calls):
        """transport records (url, headers) and returns scripted responses."""
        def transport(url, headers, timeout):
            calls.append((url, dict(headers)))
            return responses.pop(0)
        responses = self._responses
        return CanvasClient(ORIGIN, Secret(TOKEN), transport=transport, sleep=lambda _: None)

    def test_same_origin_download_sends_token_and_returns_bytes(self):
        self._responses = [Response(200, {}, b"%PDF-bytes")]
        calls = []
        client = self._client(calls)
        data = client.download(f"{ORIGIN}/files/1/download", 1024)
        self.assertEqual(data, b"%PDF-bytes")
        self.assertEqual(calls[0][1].get("Authorization"), f"Bearer {TOKEN}")

    def test_presigned_offorigin_download_sends_no_token(self):
        self._responses = [Response(200, {}, b"slidesbytes")]
        calls = []
        client = self._client(calls)
        data = client.download("https://x.cluster1.canvas-user-content.com/f?verifier=z", 1024)
        self.assertEqual(data, b"slidesbytes")
        self.assertNotIn("Authorization", calls[0][1])  # token never sent off-origin

    def test_refuses_download_from_disallowed_host(self):
        self._responses = []
        with self.assertRaises(CanvasError):
            self._client([]).download("https://evil.com/x", 1024)

    def test_byte_cap_enforced(self):
        self._responses = [Response(200, {}, b"x" * 50)]
        with self.assertRaises(CanvasError):
            self._client([]).download(f"{ORIGIN}/files/1/download", 10)


if __name__ == "__main__":
    unittest.main()
