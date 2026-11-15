import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { HttpMediaCache, type MediaFileEntry, type MediaFileStore } from '../src/lib/playback/HttpMediaCache';
import { StarterMedia } from '../src/lib/playback/StarterMedia';
import type { UnifiedItem } from '../src/features/feed/unified';
const oldUrl = 'https://cdn.example/video.mp4?private-signature=old';
const freshUrl = 'https://cdn.example/video.mp4?private-signature=new';
function fixture() {
  let clock = 100000, raw: string | null = null; let entries: MediaFileEntry[] = []; const files = new Set<string>();
  const store: MediaFileStore = {
    key: async value => createHash('sha256').update(value).digest('hex'), uri: key => `file:///cache/${key}.mp4`,
    load: async () => entries, save: async value => { entries = value; }, exists: async key => files.has(key),
    remove: async key => { files.delete(key); }, clear: async () => { files.clear(); entries = []; },
    download: async (_url, key) => { files.add(key); return 8; },
  };
  const storage = { read: async () => raw, write: async (value: string | null) => { raw = value; } };
  const cache = new HttpMediaCache(store, () => clock, 24, 8), starters = new StarterMedia(cache, storage, () => clock);
  const card = (videoId = 'provider-stable-video', kind = 'entertainment_video'): UnifiedItem => ({ item_id: 'fresh-occurrence', kind, video: { video_id: videoId, playback: { kind: 'mp4', url: freshUrl, asset_id: 'stable-asset', mime_type: 'video/mp4', expires_at: new Date(clock + 300000).toISOString() } } } as UnifiedItem);
  return { cache, starters, store, storage, files, card, raw: () => raw, advance: () => { clock += 900001; } };
}
test('completed starter survives reopen as IDs/hashes only; renewed URL gets a lease only after fresh matching authorization', async () => {
  const f = fixture(); await f.cache.open(); await f.starters.open('api:alice');
  await f.cache.warm(oldUrl, null, new AbortController().signal); await f.starters.record('provider-stable-video', 'stable-asset', oldUrl);
  assert.ok(!f.raw()!.includes('https:')); assert.ok(!f.raw()!.includes('signature')); assert.ok(!f.raw()!.includes('occurrence'));
  f.starters.deactivate(); f.cache.deactivate(); await f.cache.open(); await f.starters.open('api:alice');
  assert.deepEqual(await f.starters.preferred('api:alice'), ['provider-stable-video']);
  assert.equal(f.starters.keyFor(freshUrl), undefined);
  await f.starters.authorize('api:alice', [f.card('different-video'), f.card('provider-stable-video', 'study_video')]);
  assert.equal(f.starters.keyFor(freshUrl), undefined);
  await f.starters.authorize('api:alice', [f.card()]); const key = f.starters.keyFor(freshUrl)!;
  assert.match(await f.cache.resolveKey(key) ?? '', /^file:/);
  for (const name of ['b', 'c', 'd']) await f.cache.warm(`https://cdn.example/${name}`, null, new AbortController().signal);
  assert.ok(f.files.has(key)); // Active starter lease prevents eviction.
  await f.cache.releaseKey(key); f.advance(); assert.equal(f.starters.keyFor(freshUrl), undefined);
  assert.match(await f.cache.resolveKey(key) ?? '', /^file:/); // Retained bytes alone are not playback authorization.
});
test('wrong owner/API, logout, expiry and missing files yield no preferred starter', async () => {
  const f = fixture(); await f.cache.open(); await f.starters.open('api:alice');
  await f.cache.warm(oldUrl, null, new AbortController().signal); await f.starters.record('provider-stable-video', 'stable-asset', oldUrl);
  assert.deepEqual(await f.starters.preferred('other-api:alice'), []);
  await f.starters.open('api:bob'); assert.deepEqual(await f.starters.preferred('api:bob'), []);
  await f.starters.open('api:alice'); f.files.clear(); assert.deepEqual(await f.starters.preferred('api:alice'), []);
  await f.starters.open(null); assert.equal(f.raw(), null); assert.equal(f.starters.keyFor(freshUrl), undefined);
});
test('late hint read after account transition cannot restore another owner or playback alias', async () => {
  const f = fixture(); await f.cache.open(); await f.starters.open('api:alice');
  await f.cache.warm(oldUrl, null, new AbortController().signal); await f.starters.record('provider-stable-video', 'stable-asset', oldUrl);
  const old = f.raw(); let finish!: (value: string | null) => void;
  const other = new StarterMedia(f.cache, { read: () => new Promise(resolve => { finish = resolve; }), write: async () => {} });
  const opening = other.open('api:alice'); await new Promise(resolve => setImmediate(resolve)); other.deactivate(); finish(old); await opening;
  assert.deepEqual(await other.preferred('api:alice'), []); await other.authorize('api:alice', [f.card()]); assert.equal(other.keyFor(freshUrl), undefined);
});
test('retained bytes outlive signed URLs but require a fresh matching asset before reuse', async () => {
  const f = fixture(); await f.cache.open(); await f.starters.open('api:alice');
  await f.cache.warm(oldUrl, new Date(150000).toISOString(), new AbortController().signal);
  await f.starters.record('provider-stable-video', 'stable-asset', oldUrl); f.advance();
  assert.equal(await f.cache.resolve(oldUrl), oldUrl); // Original signed lease expired.
  assert.deepEqual(await f.starters.preferred('api:alice'), ['provider-stable-video']);
  const changed = f.card() as any; changed.video.playback.asset_id = 'replaced-asset';
  await f.starters.authorize('api:alice', [changed]); assert.equal(f.starters.keyFor(freshUrl), undefined);
  await f.starters.authorize('api:alice', []); assert.equal(f.starters.keyFor(freshUrl), undefined); // Revoked/omitted card.
  await f.starters.authorize('api:alice', [f.card()]);
  assert.match(await f.cache.resolveKey(f.starters.keyFor(freshUrl)!) ?? '', /^file:/);
});

test('fresh changed asset or quiz-only page revokes an existing same-URL cached alias', async () => {
  const f = fixture(); await f.cache.open(); await f.starters.open('api:alice');
  await f.cache.warm(oldUrl, null, new AbortController().signal); await f.starters.record('provider-stable-video', 'stable-asset', oldUrl);
  await f.starters.authorize('api:alice', [f.card()]); assert.ok(f.starters.keyFor(freshUrl));
  const replaced = f.card() as any; replaced.video.playback.asset_id = 'replacement';
  await f.starters.authorize('api:alice', [replaced]); assert.equal(f.starters.keyFor(freshUrl), undefined);
  await f.starters.authorize('api:alice', [f.card()]); assert.ok(f.starters.keyFor(freshUrl));
  await f.starters.authorize('api:alice', []); assert.equal(f.starters.keyFor(freshUrl), undefined);
});
test('late same-owner authorization cannot restore an alias revoked by a newer response', async () => {
  const f = fixture(); await f.cache.open(); await f.starters.open('api:alice');
  await f.cache.warm(oldUrl, null, new AbortController().signal); await f.starters.record('provider-stable-video', 'stable-asset', oldUrl);
  const describe = f.cache.describeKey.bind(f.cache); let release!: () => void;
  f.cache.describeKey = async key => { await new Promise<void>(resolve => { release = resolve; }); return describe(key); };
  const old = f.starters.authorize('api:alice', [f.card()]); await new Promise(resolve => setImmediate(resolve));
  await f.starters.authorize('api:alice', []); release(); await old;
  assert.equal(f.starters.keyFor(freshUrl), undefined);
});
