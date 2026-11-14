from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import contextlib
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import httpx

from app.modules.auth.service import SupabaseVerifier
from app.modules.entertainment.experiments.preview_app import create_preview_app
from app.modules.entertainment.instagram import InstagramReelsProvider, ProviderPage, make_instagram_client, normalize_reel
from app.modules.entertainment import instagram_connection
from app.modules.entertainment.instagram_connection import load_connection, save_connection
from app.modules.entertainment.live import LiveInstagramCatalog
from app.modules.entertainment.service import CatalogFailure, FEED_VALIDATOR

OWNER = '00000000-0000-4000-8000-000000000001'
OTHER = '00000000-0000-4000-8000-000000000002'
NOW = datetime(2026, 11, 14, 16, tzinfo=timezone.utc)


def reel(identifier, url=None):
    return normalize_reel(SimpleNamespace(media_type=2, product_type='clips', pk=identifier,
        code=f'synthetic{identifier}', user=SimpleNamespace(username='synthetic'),
        video_url=url or f'https://video.example.cdninstagram.com/{identifier}.mp4',
        caption_text='Synthetic Reel', video_duration=10), NOW)


class Provider:
    def __init__(self, pages):
        self.pages, self.calls, self.refreshes = list(pages), [], []
        self.closed = False

    def read_page(self, cursor):
        self.calls.append(cursor)
        page = self.pages.pop(0)
        if isinstance(page, Exception):
            raise page
        return page

    def refresh(self, identifier):
        self.refreshes.append(identifier)
        return reel(identifier, f'https://video.example.cdninstagram.com/{identifier}-fresh.mp4')

    def close(self):
        self.closed = True


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.time = 0

    def catalog(self, provider, **kwargs):
        return LiveInstagramCatalog(OWNER, provider, cursor_secret=b's' * 32,
            clock=lambda: NOW, monotonic=lambda: self.time, minimum_interval=0, **kwargs)

    def test_more_than_four_clips_preserves_provider_remainder_and_retry_stability(self):
        provider = Provider([ProviderPage([reel(i) for i in range(1, 5)], 'PRIVATE_PROVIDER_CURSOR'),
                             ProviderPage([reel(i) for i in range(4, 16)], None)])
        catalog = self.catalog(provider)
        user = {'user_id': OWNER}
        first = catalog.list_candidates(user)
        self.assertEqual(first, catalog.list_candidates(user))
        cursor, collected = first['next_cursor'], first['items'][:]
        while cursor:
            page = catalog.list_candidates(user, cursor)
            self.assertEqual(page, catalog.list_candidates(user, cursor))
            FEED_VALIDATOR.validate(page)
            collected += page['items']; cursor = page['next_cursor']
        self.assertEqual([v['provider_video_id'] for v in collected], [str(i) for i in range(1, 16)])
        self.assertEqual(provider.calls, [None, 'PRIVATE_PROVIDER_CURSOR'])
        self.assertNotIn('PRIVATE_PROVIDER_CURSOR', json.dumps(first))
        first['items'][0]['caption'] = 'Do not mutate server records'
        self.assertEqual(catalog.list_candidates(user)['items'][0]['caption'], 'Synthetic Reel')

    def test_owner_scope_cursor_tampering_query_binding_and_unknown_playback(self):
        provider = Provider([ProviderPage([reel(1)], 'private')])
        catalog = self.catalog(provider)
        for operation in (lambda: catalog.list_candidates({'user_id': OTHER}),
                          lambda: catalog.resolve_playback('instagram_1', {'user_id': OTHER}),
                          lambda: catalog.resolve_playback('instagram_1', {'user_id': OWNER})):
            with self.assertRaises(CatalogFailure) as failure:
                operation()
            self.assertEqual(failure.exception.status, 404)
        self.assertEqual(provider.calls + provider.refreshes, [])
        token = catalog.list_candidates({'user_id': OWNER})['next_cursor']
        for cursor, limit in ((token + 'x', 5), (token, 4)):
            with self.assertRaises(CatalogFailure) as failure:
                catalog.list_candidates({'user_id': OWNER}, cursor, limit)
            self.assertEqual(failure.exception.code, 'INVALID_CURSOR')
        for limit in (0, 21, True):
            with self.assertRaises(CatalogFailure):
                catalog.list_candidates({'user_id': OWNER}, limit=limit)

    def test_reload_continues_upstream_and_keeps_recent_deduplication(self):
        provider = Provider([ProviderPage([reel(1)], 'next-page'),
                             ProviderPage([reel(1), reel(2)], None)])
        catalog = self.catalog(provider)
        first = catalog.list_candidates({'user_id': OWNER})
        self.assertEqual(catalog.list_candidates({'user_id': OWNER}), first)
        self.time = 31
        second = catalog.list_candidates({'user_id': OWNER})
        self.assertEqual(provider.calls, [None, 'next-page'])
        self.assertEqual([item['provider_video_id'] for item in second['items']], ['2'])

    def test_reload_preserves_unissued_provider_leftovers(self):
        provider = Provider([ProviderPage([reel(i) for i in range(1, 9)], None)])
        catalog = self.catalog(provider)
        first = catalog.list_candidates({'user_id': OWNER}, limit=5)
        self.time = 31
        second = catalog.list_candidates({'user_id': OWNER}, limit=5)
        self.assertEqual([item['provider_video_id'] for item in second['items']], ['6', '7', '8'])
        self.assertEqual(provider.calls, [None])

    def test_repeated_provider_cursor_and_duplicates_have_a_finite_end(self):
        provider = Provider([ProviderPage([reel(1)], 'repeat'), ProviderPage([reel(1), reel(2)], 'repeat')])
        catalog = self.catalog(provider)
        first = catalog.list_candidates({'user_id': OWNER})
        second = catalog.list_candidates({'user_id': OWNER}, first['next_cursor'])
        self.assertEqual([v['provider_video_id'] for v in second['items']], ['2'])
        self.assertIsNone(second['next_cursor'])
        self.assertEqual(len(provider.calls), 2)

    def test_transient_failure_retains_cursor_and_cooldown_never_becomes_empty_success(self):
        failure = CatalogFailure(503, 'INSTAGRAM_UNAVAILABLE', 'Synthetic safe error')
        provider = Provider([ProviderPage([reel(1)], 'next'), failure, ProviderPage([reel(2)], None)])
        catalog = self.catalog(provider)
        first = catalog.list_candidates({'user_id': OWNER})
        for _ in range(2):
            with self.assertRaises(CatalogFailure):
                catalog.list_candidates({'user_id': OWNER}, first['next_cursor'])
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(catalog.list_candidates({'user_id': OWNER}), first)
        self.time = 31
        page = catalog.list_candidates({'user_id': OWNER}, first['next_cursor'])
        self.assertEqual(page['items'][0]['provider_video_id'], '2')

    def test_checkpoint_pauses_reads_until_reconnection_without_expiring_app_auth(self):
        failure = CatalogFailure(409, 'INSTAGRAM_RECONNECT_REQUIRED', 'Reconnect locally')
        provider = Provider([failure])
        catalog = self.catalog(provider)
        for moment in (0, 10000):
            self.time = moment
            with self.assertRaises(CatalogFailure) as error:
                catalog.list_candidates({'user_id': OWNER})
            self.assertEqual(error.exception.status, 409)
        self.assertEqual(len(provider.calls), 1)

    def test_playback_renews_only_known_owner_assets_and_coalesces_repeat_retries(self):
        provider = Provider([ProviderPage([reel(1)], None)])
        catalog = self.catalog(provider)
        old = catalog.list_candidates({'user_id': OWNER})['items'][0]['playback']
        fresh = catalog.resolve_playback('instagram_1', {'user_id': OWNER})
        self.assertNotEqual(old['url'], fresh['url'])
        self.assertEqual(fresh, catalog.resolve_playback('instagram_1', {'user_id': OWNER}))
        self.assertEqual(provider.refreshes, ['1'])

    def test_sustained_scrolling_is_bounded_beyond_one_hundred_reels(self):
        provider = Provider([ProviderPage([reel(i)], f'provider-page-{i}') for i in range(1, 251)])
        catalog = self.catalog(provider)
        cursor, collected, old_cursor = None, [], None
        for number in range(250):
            page = catalog.list_candidates({'user_id': OWNER}, cursor)
            collected += [v['provider_video_id'] for v in page['items']]
            cursor = page['next_cursor']
            if number == 0:
                old_cursor = cursor
        self.assertEqual(len(set(collected)), 250)
        self.assertLessEqual(len(catalog.records), 100)
        self.assertLessEqual(len(catalog.pages), 20)
        self.assertLessEqual(len(catalog.provider_cursors), 128)
        with self.assertRaises(CatalogFailure) as failure:
            catalog.list_candidates({'user_id': OWNER}, old_cursor)
        self.assertEqual(failure.exception.code, 'STALE_CURSOR')

    def test_concurrent_requests_do_not_duplicate_a_provider_read(self):
        entered, release = Event(), Event()
        provider = Provider([ProviderPage([reel(1)], None)])
        original = provider.read_page
        def slow(cursor):
            entered.set()
            if not release.wait(2):
                raise RuntimeError('test timeout')
            return original(cursor)
        provider.read_page = slow
        catalog = self.catalog(provider)
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(catalog.list_candidates, {'user_id': OWNER})
            self.assertTrue(entered.wait(1))
            try:
                with self.assertRaises(CatalogFailure) as failure:
                    catalog.list_candidates({'user_id': OWNER})
                self.assertEqual(failure.exception.code, 'INSTAGRAM_BUSY')
            finally:
                release.set()
            page = first.result()
        self.assertEqual(catalog.list_candidates({'user_id': OWNER}), page)
        self.assertEqual(len(provider.calls), 1)

    def test_expired_session_requires_reload_instead_of_silently_restarting_provider(self):
        provider = Provider([ProviderPage([reel(1)], 'next')])
        catalog = self.catalog(provider, session_seconds=60)
        first = catalog.list_candidates({'user_id': OWNER})
        self.time = 61
        with self.assertRaises(CatalogFailure) as failure:
            catalog.list_candidates({'user_id': OWNER}, first['next_cursor'])
        self.assertEqual(failure.exception.code, 'STALE_CURSOR')
        self.assertEqual(len(provider.calls), 1)

    def test_invalid_provider_metadata_becomes_a_sanitized_dependency_error(self):
        marker = 'PRIVATE_PROVIDER_RESPONSE_MUST_NOT_ESCAPE'
        catalog = self.catalog(Provider([ProviderPage([{'caption': marker}], None)]))
        with self.assertRaises(CatalogFailure) as failure:
            catalog.list_candidates({'user_id': OWNER})
        self.assertEqual(failure.exception.code, 'INSTAGRAM_INVALID_RESPONSE')
        self.assertNotIn(marker, str(failure.exception))


class ProviderTests(unittest.TestCase):
    def test_post_body_cursor_advances_past_the_initial_reels(self):
        def request(endpoint, **kwargs):
            # Model the live endpoint: query cursors are ignored, body cursors
            # select the next page. This catches apparently valid repeated pages.
            continued = kwargs.get('data', {}).get('max_id') == 'page-two'
            return {'items': [{'media': {'pk': 2 if continued else 1}}],
                    'paging_info': {'more_available': not continued, 'max_id': 'page-two'}}
        provider = InstagramReelsProvider(SimpleNamespace(authorization='synthetic', _send_private_request=request), clock=lambda: NOW)
        def extract(row):
            return SimpleNamespace(media_type=2, product_type='clips', pk=row['pk'], code='synthetic',
                user=SimpleNamespace(username='synthetic'), video_url='https://video.example.cdninstagram.com/test.mp4',
                caption_text='', video_duration=10)
        with patch('instagrapi.extractors.extract_media_v1', side_effect=extract):
            first = provider.read_page()
            second = provider.read_page(first.next_cursor)
        self.assertEqual(first.items[0]['provider_video_id'], '1')
        self.assertEqual(second.items[0]['provider_video_id'], '2')
        self.assertIsNone(second.next_cursor)

    def test_single_attempt_does_not_use_retrying_high_level_helper_or_resolve_challenges(self):
        marker = 'SYNTHETIC_SECRET_MUST_NOT_ESCAPE'
        class LoginRequired(Exception):
            pass
        calls = []
        def request(endpoint, **kwargs):
            calls.append(endpoint)
            print(marker)
            raise LoginRequired(marker)
        client = SimpleNamespace(authorization=marker, _send_private_request=request)
        provider = InstagramReelsProvider(client)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(CatalogFailure) as failure:
            provider.read_page(None)
        self.assertEqual(calls, ['clips/discover/'])
        self.assertEqual(failure.exception.code, 'INSTAGRAM_RECONNECT_REQUIRED')
        self.assertNotIn(marker, output.getvalue() + str(failure.exception))

    def test_real_provider_boundary_respects_end_flag_and_drops_ads_and_malformed_media(self):
        media = SimpleNamespace(media_type=2, product_type='clips', pk=1, code='synthetic',
            user=SimpleNamespace(username='synthetic'), video_url='https://video.example.cdninstagram.com/test.mp4',
            caption_text='', video_duration=None)
        def request(*args, **kwargs):
            return {'items': [{'media': {}}, {'is_ad': True, 'media': {}}],
                    'paging_info': {'more_available': False, 'max_id': 'DO_NOT_EXPOSE'}}
        provider = InstagramReelsProvider(SimpleNamespace(authorization='synthetic', _send_private_request=request), clock=lambda: NOW)
        with patch('instagrapi.extractors.extract_media_v1', return_value=media):
            page = provider.read_page()
        self.assertEqual(len(page.items), 1)
        self.assertIsNone(page.next_cursor)
        self.assertNotIn('DO_NOT_EXPOSE', json.dumps(page.items))

    def test_normalizer_rejects_foreign_hosts_and_credentials(self):
        for url in ('http://video.example.cdninstagram.com/clip.mp4', 'https://cdninstagram.com.evil.test/clip.mp4',
                    'https://secret:password@video.example.cdninstagram.com/clip.mp4'):
            self.assertIsNone(reel(1, url))


class ConnectionTests(unittest.TestCase):
    def test_saved_session_without_authenticated_identity_never_fetches_a_logged_out_feed(self):
        provider = Provider([])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'connection.json'
            save_connection(path, OWNER, {'cookies': {'sessionid': 'synthetic'}}, 'discover')
            with patch('sys.argv', ['connect', '--connection', str(path), '--check']), \
                 patch.object(instagram_connection, 'make_instagram_client', return_value=SimpleNamespace(user_id=None)), \
                 patch.object(instagram_connection, 'InstagramReelsProvider', return_value=provider), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(instagram_connection.main(), 1)
            report = json.loads((path.parent / 'report.json').read_text())
            self.assertEqual(report['error_code'], 'INSTAGRAM_NOT_CONNECTED')
            self.assertEqual(provider.calls, [])
            self.assertTrue(provider.closed)

    def test_interactive_setup_saves_only_session_and_reports_two_pages_without_private_output(self):
        marker, password = 'SYNTHETIC_COOKIE_MUST_NOT_ESCAPE', 'SYNTHETIC_PASSWORD_NEVER_SAVE'
        class Client:
            user_id = 1
            def login(self, *args, **kwargs):
                print(marker)
                return True
            def get_settings(self):
                return {'cookies': {'sessionid': marker}, 'password': password}
        provider = Provider([ProviderPage([reel(1)], 'private-next'), ProviderPage([reel(2)], None)])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'connection.json'
            output = io.StringIO()
            with patch('sys.argv', ['connect', '--connection', str(path), '--owner-user-id', OWNER]), \
                 patch('sys.stdin.isatty', return_value=True), \
                 patch('getpass.getpass', side_effect=['synthetic', password, '']), \
                 patch.object(instagram_connection, 'make_instagram_client', return_value=Client()), \
                 patch.object(instagram_connection, 'InstagramReelsProvider', return_value=provider), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(instagram_connection.main(), 0)
            report = json.loads((path.parent / 'report.json').read_text())
            self.assertEqual(report['pages_retrieved'], 2)
            self.assertEqual(report['unique_reels'], 2)
            self.assertEqual(report['status'], 'completed')
            self.assertNotIn(marker, output.getvalue() + json.dumps(report))
            self.assertNotIn(password, path.read_text() + output.getvalue() + json.dumps(report))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(provider.closed)

    def test_restored_sdk_session_forces_tls_timeouts_and_disables_checkpoint_handling(self):
        class Session:
            def request(self, *args, **kwargs):
                return kwargs
        class Client:
            def __init__(self, settings):
                self.settings = settings
                self.private, self.public = Session(), Session()
        with patch('instagrapi.Client', Client):
            client = make_instagram_client({'tls_verify': False, 'session_retry_total': 9})
        self.assertTrue(client.settings['tls_verify'])
        self.assertEqual(client.settings['session_retry_total'], 0)
        self.assertFalse(client.with_challenge_flow)
        for session in (client.private, client.public):
            options = session.request('GET', 'https://example.test', verify=False, allow_redirects=True)
            self.assertEqual(options['timeout'], (3, 7))
            self.assertTrue(options['verify'])
            self.assertFalse(options['allow_redirects'])

    def test_session_is_owner_bound_private_and_excludes_passwords(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'private' / 'connection.json'
            save_connection(path, OWNER, {'cookies': {'sessionid': 'SYNTHETIC_SESSION'}, 'password': 'DO_NOT_SAVE'}, 'discover')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(load_connection(path)['owner_user_id'], OWNER)
            self.assertNotIn('DO_NOT_SAVE', path.read_text())
            path.chmod(0o644)
            with self.assertRaises(CatalogFailure):
                load_connection(path)
            path.chmod(0o600)
            link = path.parent / 'symlink.json'
            link.symlink_to(path)
            with self.assertRaises(CatalogFailure):
                load_connection(link)


class LiveHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limits_keep_app_auth_valid_and_close_sdk_on_factory_shutdown(self):
        failure = CatalogFailure(503, 'INSTAGRAM_RATE_LIMITED', 'Retry in five minutes.')
        failure.retry_after = 300
        provider = Provider([failure])
        catalog = LiveInstagramCatalog(OWNER, provider, clock=lambda: NOW, minimum_interval=0)
        verifier = SupabaseVerifier('https://auth.example.test', 'synthetic', httpx.MockTransport(
            lambda request: httpx.Response(200, json={'id': OWNER, 'email': None, 'created_at': NOW.isoformat()})))
        app = create_preview_app(verifier, catalog)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://local.test') as client:
                response = await client.get('/v1/entertainment/feed', headers={'Authorization': 'Bearer owner'})
                self.assertEqual(response.status_code, 503)
                self.assertTrue(response.json()['error']['retryable'])
                self.assertEqual(response.headers['retry-after'], '300')
        self.assertTrue(provider.closed)

    async def test_live_routes_authenticate_before_provider_and_do_not_accept_query_identity(self):
        def auth(request):
            value = request.headers.get('authorization')
            if value not in ('Bearer owner', 'Bearer other'):
                return httpx.Response(401)
            return httpx.Response(200, json={'id': OWNER if value == 'Bearer owner' else OTHER,
                'email': None, 'created_at': NOW.isoformat()})
        provider = Provider([ProviderPage([reel(1)], 'private-next'), ProviderPage([reel(2)], None)])
        catalog = LiveInstagramCatalog(OWNER, provider, clock=lambda: NOW, minimum_interval=0)
        app = create_preview_app(SupabaseVerifier('https://auth.example.test', 'synthetic', httpx.MockTransport(auth)), catalog)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://local.test') as client:
            for headers, status in (({}, 401), ({'Authorization': 'Bearer invalid'}, 401), ({'Authorization': 'Bearer other'}, 404)):
                response = await client.get(f'/v1/entertainment/feed?user_id={OWNER}', headers=headers)
                self.assertEqual(response.status_code, status)
            self.assertEqual(provider.calls, [])
            headers = {'Authorization': 'Bearer owner'}
            first = await client.get('/v1/entertainment/feed', headers=headers)
            self.assertEqual(first.headers['cache-control'], 'no-store')
            second = await client.get('/v1/entertainment/feed', params={'cursor': first.json()['next_cursor']}, headers=headers)
            self.assertEqual(second.json()['items'][0]['provider_video_id'], '2')
            self.assertNotIn('private-next', second.text)
