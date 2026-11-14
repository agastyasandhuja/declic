"""Real MongoDB composition tests; Auth HTTP is explicitly mocked."""

import copy

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.integration import FeedEntertainmentReader
from app.core.migrate import (
    IDENTITY_CATALOG_MIGRATION_ID,
    apply_identity_catalog,
    apply_ordered,
)
from app.modules.auth.service import SupabaseVerifier
from app.modules.entertainment.fixtures import FixtureCatalog
from app.modules.entertainment.repository import CatalogRepository
from app.modules.entertainment.service import CatalogService
from app.runtime import create_app


def verifier():
    def handler(request):
        token = request.headers['Authorization'].removeprefix('Bearer ')
        if token not in {'alice', 'bob'}:
            return httpx.Response(401, json={})
        return httpx.Response(200, json={
            'id': 'user_' + token, 'email': None, 'created_at': '2026-11-14T00:00:00Z',
            'user_metadata': {'user_id': 'attacker'},
        })
    return SupabaseVerifier('https://auth.example.test', 'synthetic-key',
                            transport=httpx.MockTransport(handler))


def test_reader_continues_past_expired_window():
    items = FixtureCatalog().items
    valid = next(item for item in items if item['availability'] == 'ready'
                 and item['playback']['kind'] != 'embed')
    records = []
    for i in range(21):
        record = copy.deepcopy(valid)
        record['video_id'] = f'video_{i}'
        record['provider_video_id'] = str(i)
        record['playback']['expires_at'] = '2000-01-01T00:00:00Z' if i < 20 else None
        records.append(record)

    class Repository:
        def read_items(self, user):
            assert user['user_id'] == 'owner'
            return records

    result = FeedEntertainmentReader(CatalogService(Repository())).list_candidates('owner', 1)
    assert [item.video_id for item in result] == ['video_20']


def test_integrated_http_identity_catalog_feed_and_restart(database):
    if database.mongo is None:
        pytest.skip('Set API_TEST_MONGODB_URI for real database integration')
    apply_ordered(database, include_videos=True, include_identity_catalog=True)
    apply_ordered(database, include_videos=True, include_identity_catalog=True)
    settings = database.settings.model_copy(update={'environment': 'development'})
    items = FixtureCatalog().items
    # Explicit synthetic catalog; does not call Instagram or upload media.
    CatalogRepository(database.mongo).replace_catalog({'user_id': 'user_alice'}, items)

    def app():
        return create_app(settings=settings, database=database, verifier=verifier())

    with TestClient(app()) as client:
        for path in ['/v1/me', '/v1/entertainment/feed', '/v1/learning/progress']:
            assert client.get(path).status_code == 401
            assert client.get(path, headers={'Authorization': 'Bearer invalid'}).status_code == 401
        client.headers['Authorization'] = 'Bearer alice'
        assert client.get('/v1/me').json()['user_id'] == 'user_alice'
        patch = {'expected_revision': 0, 'display_name': 'Synthetic learner'}
        assert client.patch('/v1/me', json=patch).status_code == 200
        assert client.patch('/v1/me', json=patch).status_code == 409
        page = client.get('/v1/entertainment/feed').json()
        assert page['items']
        session = client.post('/v1/feed/sessions', json={}).json()['session_id']
        feed = client.get('/v1/feed', params={'session_id': session, 'limit': 5})
        assert feed.status_code == 200, feed.text
        assert feed.json()['items']
        client.headers['Authorization'] = 'Bearer bob'
        assert client.get('/v1/me').json()['display_name'] is None
        assert client.get('/v1/entertainment/feed').status_code == 404
        assert client.get('/v1/feed', params={'session_id': session}).status_code == 404
        video_id = page['items'][0]['video_id']
        assert client.get(f'/v1/entertainment/videos/{video_id}/playback').status_code == 404
    with TestClient(app()) as client:
        client.headers['Authorization'] = 'Bearer alice'
        assert client.get('/v1/me').json()['display_name'] == 'Synthetic learner'
        assert client.get('/v1/feed', params={'session_id': session, 'limit': 5}).status_code == 200


def test_identity_migration_conflict_keeps_schema_and_no_marker(database):
    if database.mongo is None:
        pytest.skip('Set API_TEST_MONGODB_URI')
    database.mongo.create_collection('app_profiles', validator={'user_id': {'$type': 'string'}})
    with pytest.raises(RuntimeError, match='existing validator differs'):
        apply_identity_catalog(database)
    assert database.mongo.api_migrations.find_one({'_id': IDENTITY_CATALOG_MIGRATION_ID}) is None
    assert database.mongo.app_profiles.options()['validator'] == {'user_id': {'$type': 'string'}}


def test_feed_snapshot_reads_once_and_never_reuses_another_owner_or_revision():
    valid = next(item for item in FixtureCatalog().items if item['availability'] == 'ready'
                 and item['playback']['kind'] != 'embed')
    records = []
    for i in range(100):
        record = copy.deepcopy(valid)
        record.update(video_id=f'video_{i}', provider_video_id=str(i))
        record['playback']['expires_at'] = None
        records.append(record)

    class Repository:
        calls = 0
        def read_items(self, user):
            self.calls += 1
            return records if user['user_id'] == 'owner' else []

    repository = Repository()
    reader = FeedEntertainmentReader(CatalogService(repository))
    assert len(reader.list_candidates('owner', 200)) == 100
    assert repository.calls == 1
    assert reader.list_candidates('other', 200) == []
    records.clear()  # A disconnect/replacement cannot leave a process-local stale batch.
    assert reader.list_candidates('owner', 200) == []
