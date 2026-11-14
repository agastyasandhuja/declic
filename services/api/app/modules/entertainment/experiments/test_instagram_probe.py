import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import instagram_probe as probe


class ProbeTests(unittest.TestCase):
    def test_media_filter_keeps_only_unique_reels_and_https_candidates(self):
        def media(identifier, kind=2, product="clips", url="https://example.test/clip.mp4"):
            return SimpleNamespace(pk=identifier, media_type=kind, product_type=product,
                                   video_url=url, code="example", user=SimpleNamespace(username="synthetic"),
                                   caption_text="Synthetic clip", video_duration=10)
        result = probe.summarize_media([media(1), media(1), media(2, kind=1),
                                        media(3, product="feed"), media(4, url="http://unsafe.test/clip")])
        self.assertEqual([item["provider_video_id"] for item in result], ["1", "4"])
        self.assertIsNone(result[1]["candidate_playback_url"])
        self.assertEqual(set(result[0]), {"provider_video_id", "source_url", "creator_handle",
                                          "caption", "duration_seconds", "candidate_playback_url"})

    def test_output_stays_in_ignored_repo_local_directory_with_private_permissions(self):
        self.assertTrue((probe.ROOT / "AGENTS.md").exists())
        self.assertEqual(probe.OUTPUT, probe.ROOT / ".local" / "instagram-probe")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "report.json"
            target.write_text("old")
            target.chmod(0o644)
            probe.write_private(target, {"stage": "test"})
            self.assertEqual(json.loads(target.read_text()), {"stage": "test"})
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_failed_provider_login_cannot_leak_logs_or_exception_payload(self):
        secret = "TEST_ONLY_SESSION_DO_NOT_EXPORT"
        session = SimpleNamespace(request=lambda: None, close=lambda: None)
        class FakeClient:
            def __init__(self, **_kwargs):
                self.private = self.public = session
            def login(self, *_args, **_kwargs):
                print(secret)
                raise RuntimeError(secret)
        with tempfile.TemporaryDirectory() as folder:
            output = io.StringIO()
            with patch.object(probe, "OUTPUT", Path(folder)), patch("sys.argv", ["probe"]), \
                 patch("sys.stdin.isatty", return_value=True), \
                 patch("getpass.getpass", side_effect=["synthetic", "TEST_PASSWORD", ""]), \
                 patch("instagrapi.Client", FakeClient), contextlib.redirect_stdout(output):
                self.assertEqual(probe.main(), 1)
            report = (Path(folder) / "report.json").read_text()
            self.assertNotIn(secret, output.getvalue() + report)
            self.assertNotIn("TEST_PASSWORD", output.getvalue() + report)
            self.assertEqual(json.loads(report)["stage"], "failed")
            self.assertFalse(json.loads(report)["authenticated"])
            self.assertFalse((Path(folder) / "catalog.json").exists())

    def test_pagination_uses_provider_cursor_deduplicates_and_stops_at_end(self):
        def media(identifier):
            return SimpleNamespace(pk=identifier, media_type=2, product_type='clips', video_url='https://example.test/clip.mp4', code='synthetic', user=SimpleNamespace(username='synthetic'), caption_text='', video_duration=10)
        calls = []
        pages = [{'items': [{'media': media(1)}], 'paging_info': {'max_id': 'page-two'}},
                 {'items': [{'media': media(1)}, {'media': media(2)}], 'paging_info': {}}]
        def request(endpoint, **kwargs):
            calls.append((endpoint, kwargs['params']['max_id'])); return pages.pop(0)
        client = SimpleNamespace(private_request=request)
        items, summary = probe.retrieve_pages(client, 'discover', 5, 3, lambda value: value)
        self.assertEqual(calls, [('clips/discover/', ''), ('clips/discover/', 'page-two')])
        self.assertEqual([item['provider_video_id'] for item in items], ['1', '2'])
        self.assertEqual(summary['stop_reason'], 'end')
        self.assertEqual(summary['pages_retrieved'], 2)
        self.assertNotIn('page-two', json.dumps(summary))

    def test_repeated_cursors_are_bounded_and_provider_failure_is_not_empty_success(self):
        calls = []
        def repeated(endpoint, **kwargs):
            calls.append(endpoint); return {'items': [], 'paging_info': {'max_id': 'repeat'}}
        _, summary = probe.retrieve_pages(SimpleNamespace(private_request=repeated), 'connected', 5, 3, lambda value: value)
        self.assertEqual(len(calls), 2)
        self.assertEqual(summary['stop_reason'], 'repeated_cursor')
        def fail(*args, **kwargs):
            raise RuntimeError('SYNTHETIC_PROVIDER_FAILURE')
        with self.assertRaises(RuntimeError):
            probe.retrieve_pages(SimpleNamespace(private_request=fail), 'discover', 5, 2, lambda value: value)
        with self.assertRaises(ValueError):
            probe.retrieve_pages(SimpleNamespace(private_request=fail), 'discover', 5, 99, lambda value: value)


if __name__ == "__main__":
    unittest.main()
