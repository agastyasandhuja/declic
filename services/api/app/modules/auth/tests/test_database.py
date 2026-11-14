"""Real MongoDB tests, opt-in only; each run drops only its fresh synthetic DB."""
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import unittest
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, WriteError

from app.modules.auth.database_setup import apply_domain_drafts
from app.modules.auth.repository import ProfileRepository
from app.modules.auth.service import AuthFailure
from app.modules.entertainment.repository import CatalogRepository
from app.modules.entertainment.service import CatalogFailure, CatalogService, ROOT

USER = {'user_id': 'user_synthetic_01', 'email': None, 'display_name': None, 'timezone': 'UTC', 'created_at': '2026-11-14T00:00:00Z'}
OTHER = {**USER, 'user_id': 'user_synthetic_02'}


@unittest.skipUnless(os.getenv('MONGODB_TEST_URI'), 'Set MONGODB_TEST_URI for a disposable synthetic database.')
class MongoTests(unittest.TestCase):
    def setUp(self):
        self.client = MongoClient(os.environ['MONGODB_TEST_URI'], serverSelectionTimeoutMS=3000, timeoutMS=5000, tz_aware=True)
        self.name = 'adi_test_' + uuid4().hex
        self.database = self.client[self.name]
        apply_domain_drafts(self.database)
        self.items = json.loads((ROOT / 'fixtures/entertainment/feed.json').read_text())['items']

    def tearDown(self):
        self.client.drop_database(self.name)
        self.client.close()

    def test_repeatable_drafts_and_database_validators(self):
        apply_domain_drafts(self.database)
        with self.assertRaises(WriteError):
            self.database.app_profiles.insert_one({'user_id': USER['user_id']})
        repo = CatalogRepository(self.database)
        repo.replace_catalog(USER, self.items)
        with self.assertRaises(WriteError):
            self.database.entertainment_catalogs.update_one({'user_id': USER['user_id']}, {'$set': {'items.0.playback.url': 'http://insecure.test/clip.mp4'}})
        with self.assertRaises(DuplicateKeyError):
            document = self.database.entertainment_catalogs.find_one({'user_id': USER['user_id']})
            del document['_id']
            self.database.entertainment_catalogs.insert_one(document)
        self.assertEqual(self.database.entertainment_catalogs.index_information()['catalog_expiry']['expireAfterSeconds'], 0)

    def test_profile_revision_identity_and_cross_user_isolation(self):
        repo = ProfileRepository(self.database)
        self.assertEqual(repo.get_profile(USER)['revision'], 0)
        updated = repo.update_profile(USER, 0, {'timezone': 'America/New_York', 'display_name': 'Synthetic'})
        self.assertEqual(updated['revision'], 1)
        self.assertEqual(repo.get_profile(OTHER)['display_name'], None)
        for revision in (0, 2):
            with self.assertRaises(AuthFailure) as raised:
                repo.update_profile(USER, revision, {'display_name': 'Stale'})
            self.assertEqual(raised.exception.status, 409)
        for patch in ({'user_id': OTHER['user_id']}, {'timezone': 'not/a/timezone'}, {'display_name': {'$ne': None}}):
            with self.assertRaises(AuthFailure):
                repo.update_profile(USER, 1, patch)
        self.assertEqual(repo.update_profile(USER, 1, {'display_name': None})['revision'], 2)
        self.assertEqual(repo.get_profile(USER)['user_id'], USER['user_id'])

    def test_owned_catalog_pagination_tampering_and_atomic_replacement(self):
        repo = CatalogRepository(self.database)
        repo.replace_catalog(USER, self.items)
        repo.replace_catalog(OTHER, self.items)
        service = CatalogService(repo, cursor_secret=b's' * 32)
        first = service.list_candidates(USER, limit=2)
        second = service.list_candidates(USER, first['next_cursor'], 2)
        last = service.list_candidates(USER, second['next_cursor'], 2)
        self.assertEqual(len(first['items'] + second['items'] + last['items']), 5)
        self.assertIsNone(last['next_cursor'])
        for cursor, user, limit in ((first['next_cursor'] + 'x', USER, 2), (first['next_cursor'], OTHER, 2), (first['next_cursor'], USER, 3)):
            with self.assertRaises(CatalogFailure) as raised:
                service.list_candidates(user, cursor, limit)
            self.assertEqual(raised.exception.status, 422)
        repo.replace_catalog(USER, self.items[:1])
        with self.assertRaises(CatalogFailure) as raised:
            service.list_candidates(USER, first['next_cursor'], 2)
        self.assertEqual(raised.exception.code, 'STALE_CURSOR')
        self.assertEqual(len(service.list_candidates(OTHER)['items']), 5)

    def test_expiry_unavailability_and_credential_exclusion(self):
        now = datetime.now(timezone.utc)
        repo = CatalogRepository(self.database, clock=lambda: now)
        values = copy.deepcopy(self.items)
        values[0]['playback']['expires_at'] = (now - timedelta(seconds=1)).isoformat()
        values[1]['availability'] = 'unavailable'
        values[2]['provider_cookie'] = 'SYNTHETIC_SECRET'
        values[2]['creator']['private'] = 'SYNTHETIC_SECRET'
        repo.replace_catalog(USER, values + values[:1])
        self.assertNotIn('SYNTHETIC_SECRET', str(self.database.entertainment_catalogs.find_one()))
        service = CatalogService(repo, clock=lambda: now)
        self.assertEqual(len(service.list_candidates(USER)['items']), 3)
        with self.assertRaises(CatalogFailure) as raised:
            service.resolve_playback(values[0]['video_id'], USER)
        self.assertEqual(raised.exception.status, 410)
        future_reader = CatalogRepository(self.database, clock=lambda: now + timedelta(hours=2))
        with self.assertRaises(CatalogFailure):
            future_reader.read_items(USER)
        self.assertIsNotNone(self.database.entertainment_catalogs.find_one())  # access checks do not await TTL deletion


    def test_http_profile_and_catalog_use_verified_subject_with_real_database(self):
        import asyncio
        import httpx
        from app.modules.auth.service import SupabaseVerifier
        from app.modules.entertainment.experiments.preview_app import create_preview_app
        repo = CatalogRepository(self.database)
        repo.replace_catalog(USER, self.items)
        verifier = SupabaseVerifier('https://auth.example.test', 'synthetic', httpx.MockTransport(lambda request: httpx.Response(200, json={'id': USER['user_id'], 'email': None, 'created_at': USER['created_at']})))
        app = create_preview_app(verifier, CatalogService(repo), ProfileRepository(self.database))
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://local.test', headers={'Authorization': 'Bearer synthetic'}) as client:
                self.assertEqual((await client.get('/v1/me')).json()['revision'], 0)
                result = await client.patch('/v1/me', json={'expected_revision': 0, 'timezone': 'America/New_York'})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()['user_id'], USER['user_id'])
                self.assertEqual((await client.get('/v1/me')).json()['timezone'], 'America/New_York')
                self.assertEqual((await client.patch('/v1/me', json={'expected_revision': 0, 'timezone': 'UTC'})).status_code, 409)
                self.assertEqual((await client.patch('/v1/me', json={'expected_revision': 1, 'user_id': OTHER['user_id']})).status_code, 422)
                self.assertEqual(len((await client.get('/v1/entertainment/feed?limit=2')).json()['items']), 2)
        asyncio.run(scenario())


if __name__ == '__main__':
    unittest.main()
