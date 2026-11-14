import json
from pathlib import Path
import tempfile
import unittest

import httpx

from app.modules.auth.service import AuthFailure, SupabaseVerifier
from app.modules.entertainment.experiments.preview_app import create_preview_app
from app.modules.entertainment.service import SavedCatalog

OWNER = '00000000-0000-4000-8000-000000000001'
OTHER = '00000000-0000-4000-8000-000000000002'
VIDEO = {'schema_version': '1', 'video_id': 'instagram_synthetic', 'provider': 'instagram',
         'provider_video_id': '10001', 'source_url': 'https://www.instagram.com/reel/synthetic/',
         'creator': {'handle': 'synthetic', 'display_name': 'Synthetic', 'attribution_url': None},
         'caption': 'Synthetic test clip', 'duration_seconds': 10, 'thumbnail_url': None,
         'acquired_at': '2026-11-14T08:00:00Z', 'availability': 'ready', 'acquisition_mode': 'cached',
         'playback': {'kind': 'mp4', 'asset_id': 'synthetic_asset', 'url': 'https://video.example.test/test.mp4', 'expires_at': None, 'mime_type': 'video/mp4'}}


class PreviewApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        directory = Path(self.folder.name)
        self.owner_path, self.catalog_path = directory / 'owner.json', directory / 'feed.json'
        self.owner_path.write_text(json.dumps({'user_id': OWNER}))
        self.catalog_path.write_text(json.dumps({'schema_version': '1', 'items': [VIDEO], 'next_cursor': None}))
        self.auth_requests = 0
        def auth_server(request):
            self.auth_requests += 1
            self.assertEqual(request.url.host, 'auth.example.test')
            self.assertEqual(request.headers['apikey'], 'synthetic-publishable-key')
            token = request.headers.get('authorization')
            if token not in ('Bearer owner-token', 'Bearer other-token'):
                return httpx.Response(401, json={'message': 'PRIVATE_PROVIDER_ERROR'})
            identifier = OWNER if token == 'Bearer owner-token' else OTHER
            return httpx.Response(200, json={'id': identifier, 'email': 'synthetic@example.test',
                                            'created_at': '2026-11-14T08:00:00Z',
                                            'user_metadata': {'user_id': OWNER, 'role': 'admin'}})
        verifier = SupabaseVerifier('https://auth.example.test', 'synthetic-publishable-key', httpx.MockTransport(auth_server))
        self.service = SavedCatalog(self.catalog_path, self.owner_path)
        self.app = create_preview_app(verifier, self.service)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://local.test')

    async def asyncTearDown(self):
        await self.client.aclose()
        self.folder.cleanup()

    async def test_missing_invalid_and_expired_tokens_are_rejected_without_catalog(self):
        self.catalog_path.unlink()
        for headers in ({}, {'Cookie': 'sessionid=provider-cookie'}, {'Authorization': 'Bearer forged-token'}, {'Authorization': 'Bearer expired-token'}):
            response = await self.client.get('/v1/entertainment/feed', headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn('error', response.json())
            self.assertNotIn('PRIVATE_PROVIDER_ERROR', response.text)

    async def test_owner_gets_saved_feed_and_playback_with_no_cache(self):
        headers = {'Authorization': 'Bearer owner-token'}
        response = await self.client.get('/v1/entertainment/feed', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['items'], [VIDEO])
        self.assertEqual(response.headers['cache-control'], 'no-store')
        playback = await self.client.get('/v1/entertainment/videos/instagram_synthetic/playback', headers=headers)
        self.assertEqual(playback.status_code, 200)
        self.assertEqual(playback.json(), VIDEO['playback'])

    async def test_other_user_and_forged_query_identity_cannot_read_catalog(self):
        self.catalog_path.unlink()  # A non-owner must be rejected before private I/O.
        headers = {'Authorization': 'Bearer other-token'}
        for route in (f'/v1/entertainment/feed?user_id={OWNER}', '/v1/entertainment/videos/instagram_synthetic/playback'):
            response = await self.client.get(route, headers=headers)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn('Synthetic test clip', response.text)
        me = await self.client.get('/v1/me', headers=headers)
        self.assertEqual(me.json()['user_id'], OTHER)  # Metadata cannot impersonate OWNER.

    async def test_unbound_catalog_is_not_given_to_first_authenticated_caller(self):
        self.owner_path.unlink()
        response = await self.client.get('/v1/entertainment/feed', headers={'Authorization': 'Bearer owner-token'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'PREVIEW_NOT_BOUND')

    async def test_invalid_limits_cursors_and_unknown_videos_are_bounded(self):
        headers = {'Authorization': 'Bearer owner-token'}
        for route, status in (('/v1/entertainment/feed?limit=999', 422), ('/v1/entertainment/feed?cursor=foreign', 422), ('/v1/entertainment/videos/missing/playback', 404)):
            response = await self.client.get(route, headers=headers)
            self.assertEqual(response.status_code, status)
            self.assertIn('error', response.json())

    async def test_auth_network_failures_and_redirects_do_not_become_success_or_leak_tokens(self):
        for status in (302, 500):
            verifier = SupabaseVerifier('https://auth.example.test', 'synthetic-key', httpx.MockTransport(lambda request: httpx.Response(status, headers={'Location': 'https://evil.example.test'})))
            with self.assertRaises(AuthFailure) as raised:
                await verifier.verify_access_token('DO_NOT_EXPOSE')
            self.assertEqual(raised.exception.status, 503)
            self.assertNotIn('DO_NOT_EXPOSE', str(raised.exception))
        def timeout(request):
            raise httpx.ReadTimeout('PRIVATE_PROVIDER_ERROR')
        verifier = SupabaseVerifier('https://auth.example.test', 'synthetic-key', httpx.MockTransport(timeout))
        with self.assertRaises(AuthFailure) as raised:
            await verifier.verify_access_token('DO_NOT_EXPOSE')
        self.assertEqual(raised.exception.status, 503)


if __name__ == '__main__':
    unittest.main()


class CursorTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        directory = Path(self.folder.name)
        self.owner, self.catalog = directory / 'owner.json', directory / 'feed.json'
        self.owner.write_text(json.dumps({'user_id': OWNER}))
        self.items = [{**VIDEO, 'video_id': f'video_{i}', 'provider_video_id': str(i)} for i in range(5)]
        self.catalog.write_text(json.dumps({'schema_version': '1', 'items': self.items, 'next_cursor': None}))
        self.service = SavedCatalog(self.catalog, self.owner, cursor_secret=b's' * 32)

    def tearDown(self):
        self.folder.cleanup()

    def test_small_pages_retrieve_entire_batch_once(self):
        cursor, collected = None, []
        for _ in range(4):
            page = self.service.list_candidates({'user_id': OWNER}, cursor, 2)
            collected.extend(page['items'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        self.assertEqual([v['video_id'] for v in collected], [v['video_id'] for v in self.items])
        self.assertIsNone(cursor)

    def test_changed_batch_invalidates_cursor_and_wrong_query_cannot_reuse_it(self):
        from app.modules.entertainment.service import CatalogFailure
        cursor = self.service.list_candidates({'user_id': OWNER}, limit=2)['next_cursor']
        with self.assertRaises(CatalogFailure) as changed:
            self.service.list_candidates({'user_id': OWNER}, cursor, 3)
        self.assertEqual(changed.exception.status, 422)
        self.catalog.write_text(json.dumps({'schema_version': '1', 'items': self.items[:1], 'next_cursor': None}))
        with self.assertRaises(CatalogFailure) as stale:
            self.service.list_candidates({'user_id': OWNER}, cursor, 2)
        self.assertEqual(stale.exception.status, 409)
