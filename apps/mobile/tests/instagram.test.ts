import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeInstagramCatalog } from '../scripts/instagram-catalog';
import { createSavedInstagramSource } from '../src/features/feed/source';
const { previewCatalogPath, isLoopback } = require('../scripts/instagram-preview.cjs');

const clip = { provider_video_id: '10001', creator_handle: 'synthetic_creator', caption: 'A synthetic Reel', duration_seconds: 12, source_url: 'https://www.instagram.com/reel/synthetic/', candidate_playback_url: 'https://video.example.cdninstagram.com/synthetic.mp4' };
const catalog = { acquired_at: '2026-11-14T08:00:00+00:00', items: [clip] };

test('Instagram normalization preserves stable identity/order and excludes provider credentials', () => {
  const page = normalizeInstagramCatalog({ ...catalog, cookies: { sessionid: 'DO_NOT_EXPORT' }, items: [{ ...clip, headers_ref: 'DO_NOT_EXPORT' }, clip, { ...clip, provider_video_id: '10002' }] });
  assert.deepEqual(page.items.map(item => item.video_id), ['instagram_10001', 'instagram_10002']);
  assert.ok(page.items.every(item => item.provider === 'instagram' && item.acquisition_mode === 'cached' && item.acquired_at === catalog.acquired_at));
  assert.equal(page.next_cursor, null);
  assert.equal(page.items[0].playback.expires_at, null);
  assert.ok(!JSON.stringify(page).includes('DO_NOT_EXPORT'));
});
test('untrusted Instagram metadata rejects foreign media hosts, userinfo, insecure URLs and naive dates', () => {
  for (const url of ['http://video.example.cdninstagram.com/clip.mp4', 'https://cdninstagram.com.evil.test/clip.mp4', 'https://cookie:secret@video.example.cdninstagram.com/clip.mp4']) {
    assert.throws(() => normalizeInstagramCatalog({ ...catalog, items: [{ ...clip, candidate_playback_url: url }] }));
  }
  assert.throws(() => normalizeInstagramCatalog({ ...catalog, acquired_at: '2026-11-14T08:00:00' }));
  assert.throws(() => normalizeInstagramCatalog({ ...catalog, items: [{ ...clip, duration_seconds: -1 }] }));
  assert.throws(() => normalizeInstagramCatalog({ ...catalog, items: [] }));
});
test('saved Instagram adapter has a finite batch and cannot imply live pagination or URL refresh', async () => {
  const source = createSavedInstagramSource(normalizeInstagramCatalog(catalog));
  const page = await source.getPage();
  assert.equal(source.mode, 'saved_instagram'); assert.equal(page.items.length, 1); assert.equal(page.next_cursor, null);
  await assert.rejects(source.getPage('next-page'));
  assert.deepEqual(await source.resolvePlayback(page.items[0].video_id), page.items[0].playback);
  await assert.rejects(source.resolvePlayback('missing-video'));
});
test('private Instagram catalog only resolves for an explicitly enabled development iOS bundle', () => {
  const options = { appRoot: '/repo/apps/mobile', enabled: true, dev: true, platform: 'ios' };
  assert.equal(previewCatalogPath(options), '/repo/.local/instagram-probe/feed.v1.json');
  for (const patch of [{ enabled: false }, { dev: false }, { platform: 'android' }, { platform: 'web' }]) {
    assert.equal(previewCatalogPath({ ...options, ...patch }), '/repo/apps/mobile/src/development/emptyInstagramCatalog.json');
  }
  assert.ok(isLoopback('127.0.0.1')); assert.ok(isLoopback('::1')); assert.ok(isLoopback('::ffff:127.0.0.1'));
  assert.ok(!isLoopback('192.168.1.2')); assert.ok(!isLoopback(undefined));
});
