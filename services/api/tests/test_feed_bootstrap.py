"""Startup hints never replace authorization, ranking policy or quiz gates."""
import uuid

import pytest

from conftest import reached_quiz, watch


def bootstrap(client, ids=(), key=None):
    return client.post('/v1/feed/bootstrap', json={
        'limit': 5, 'preferred_video_ids': list(ids),
    }, headers={'Idempotency-Key': key or str(uuid.uuid4())})


def clips(catalog):
    catalog.objectives = []
    base = catalog.clips[0]
    catalog.clips = [base.model_copy(update={
        'video_id': f'reel_{i:03}', 'provider_video_id': str(i),
    }) for i in range(10)]


def test_cached_first_clip_then_normal_inventory_and_retry(client, catalog):
    clips(catalog)
    key = str(uuid.uuid4())
    response = bootstrap(client, ['reel_008'], key)
    assert response.status_code == 200, response.text
    page = response.json()
    assert [i['video']['video_id'] for i in page['items']] == [
        'reel_008', 'reel_000', 'reel_001', 'reel_002', 'reel_003',
    ]
    assert bootstrap(client, ['reel_008'], key).json() == page
    assert bootstrap(client, ['reel_009'], key).status_code == 409
    next_page = client.get('/v1/feed', params={
        'session_id': page['session_id'], 'cursor': page['next_cursor'], 'limit': 5,
    })
    assert next_page.status_code == 200, next_page.text
    assert next_page.json()['items'][0]['video']['video_id'] == 'reel_004'


def test_invalid_and_immediate_repeat_hints_ignored(client, catalog, clock):
    clips(catalog)
    catalog.clips[8] = catalog.clips[8].model_copy(update={'availability': 'unavailable'})
    catalog.clips[9] = catalog.clips[9].model_copy(update={'playback':
        catalog.clips[9].playback.model_copy(update={'expires_at': clock()})})
    first = bootstrap(client, ['another_users_video', 'reel_008', 'reel_009']).json()
    assert first['items'][0]['video']['video_id'] == 'reel_000'
    last = first['items'][-1]['video']['video_id']
    watch(client, clock, first['session_id'], first['items'][-1])
    second = bootstrap(client, [last]).json()
    assert second['items'][0]['video']['video_id'] != last


def test_retry_revalidates_revoked_catalog_content(client, catalog):
    clips(catalog)
    key = str(uuid.uuid4())
    first = bootstrap(client, ['reel_008'], key).json()
    catalog.clips = [c for c in catalog.clips if c.video_id != 'reel_008']
    retry = bootstrap(client, ['reel_008'], key).json()
    assert retry['session_id'] == first['session_id']
    assert 'reel_008' not in [i['video']['video_id'] for i in retry['items']]


@pytest.mark.parametrize('activate', [False, True])
def test_scheduled_and_active_quiz_survive_bootstrap(client, clock, activate):
    session, quiz, _ = reached_quiz(client, clock)
    if activate:
        response = client.post(f'/v1/feed/sessions/{session}/quiz-gate', json={
            'quiz_instance_id': quiz['quiz']['quiz_instance_id'], 'item_id': quiz['item_id'],
        })
        assert response.status_code == 200, response.text
    response = bootstrap(client, ['ent_demo_01'])
    assert response.status_code == 200, response.text
    assert response.json()['items'] == [quiz]
    assert response.json()['session_id'] == session


def test_bootstrap_does_not_suppress_due_study_slot(client, app, catalog, database):
    from app.modules.recommendations import repository as repo
    session = app.state.feed.start_session('user_demo_01')['session_id']
    def due(conn):
        state = repo.get_session(conn, 'user_demo_01', session)
        state['study_debt'] = 1
        repo.save_session(conn, 'user_demo_01', state)
    database.run('user_demo_01', due)
    page = bootstrap(client, [catalog.clips[0].video_id]).json()
    assert page['items'][0]['kind'] == 'study_video'


def test_bootstrap_auth_and_bounded_hint_schema(client, app):
    denied = client.post('/v1/feed/bootstrap', json={}, headers={'Authorization': ''})
    assert denied.status_code == 401
    assert bootstrap(client, ['id'] * 7).status_code == 422
    assert bootstrap(client, ['https://untrusted.example/video']).status_code == 422
    assert client.post('/v1/feed/bootstrap', json={}).status_code == 422
    first = bootstrap(client).json()
    client.headers['Authorization'] = 'Bearer ' + app.state.identity.tokens['user_demo_02']
    second = bootstrap(client).json()
    assert second['session_id'] != first['session_id']
    assert not ({i['item_id'] for i in first['items']} & {i['item_id'] for i in second['items']})
