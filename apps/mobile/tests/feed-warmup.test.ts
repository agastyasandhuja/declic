import test from 'node:test';
import assert from 'node:assert/strict';
import { MediaWarmup, hasBufferHeadroom } from '../src/lib/playback/MediaWarmup';
import { CommentsCache, commentsFor } from '../src/features/feed/CommentsCache';
import { compactCount } from '../src/features/feed/engagement';
import { FeedInteraction, interactionGates } from '../src/lib/playback/FeedInteraction';
import { VisibleWatchTracker } from '../src/lib/playback/VisibleWatchTracker';

const asset = (i: number) => ({ url: `https://example.test/${i}.mp4`, kind: 'mp4', expires_at: null });
const tick = () => new Promise<void>(resolve => setImmediate(resolve));
test('serial warmup keeps six MP4 starts, cancels stale work, never starts while disabled', async () => {
  const loads: { url: string; signal: AbortSignal; end(): void }[] = [];
  let stops = 0;
  const queue = new MediaWarmup({ warm: (url, signal) => new Promise<void>(resolve => loads.push({ url, signal, end: resolve })), stop: () => stops++ });
  queue.update(Array.from({ length: 10 }, (_, i) => asset(i)), false); assert.equal(loads.length, 0);
  queue.update(Array.from({ length: 10 }, (_, i) => asset(i)), true); assert.equal(loads.length, 1);
  for (let i = 0; i < 6; i++) { loads[i].end(); await tick(); }
  assert.equal(loads.length, 6);
  queue.update([asset(11), asset(12)], true); assert.equal(loads.length, 7);
  queue.update([asset(20)], true); assert.ok(loads[6].signal.aborted); assert.equal(loads.length, 7);
  loads[6].end(); await tick(); assert.equal(loads[7].url, asset(20).url);
  queue.update([], false); assert.ok(loads[7].signal.aborted); assert.ok(stops >= 2);
  queue.dispose(); loads[7].end(); await tick(); assert.equal(loads.length, 8);
});
test('warmup excludes HLS, expiring and unsafe URLs and requires buffer headroom', async () => {
  const urls: string[] = [];
  const queue = new MediaWarmup({ warm: async url => { urls.push(url); }, stop() {} }, () => 100000);
  queue.update([{ ...asset(1), kind: 'hls' }, { ...asset(2), expires_at: new Date(120000).toISOString() }, { ...asset(3), url: 'http://example.test/a' }, asset(4)], true);
  await tick(); assert.deepEqual(urls, [asset(4).url]);
  assert.equal(hasBufferHeadroom(-1, 0, 10), false); assert.equal(hasBufferHeadroom(1, 0, 10), false);
  assert.equal(hasBufferHeadroom(5, 3, 10), true); assert.equal(hasBufferHeadroom(1, 0, 1), true);
  queue.dispose();
});
const page = { schema_version: '1', availability: 'available', items: [{ comment_id: 'c', text: 'Real text', author: { username: 'user' }, like_count: 33000 }], next_cursor: null };
test('comments reuse only first page, expire and evict, and isolate explicit owner plus API', async () => {
  let calls = 0; let now = 0;
  const api = { request: async () => { calls++; return page as any; } };
  const cache = new CommentsCache(api, () => now); const signal = new AbortController().signal;
  await cache.read('1', null, signal); await cache.read('1', null, signal); assert.equal(calls, 1);
  await cache.read('1', 'next', signal); assert.equal(calls, 2);
  for (let i = 2; i <= 13; i++) await cache.read(String(i), null, signal);
  assert.equal(cache.peek('1'), null); assert.ok(cache.peek('13')); now = 60001; assert.equal(cache.peek('13'), null);
  const a = commentsFor(api, 'owner-a'); await a.read('1', null, signal);
  assert.equal(commentsFor(api, 'owner-b').peek('1'), null);
  assert.equal(commentsFor({ request: api.request }, 'owner-a').peek('1'), null);
});
test('opening comments adopts pending warmup; last subscriber cancellation aborts and never caches', async () => {
  let resolve!: (v: unknown) => void; let fetchSignal!: AbortSignal; let calls = 0;
  const cache = new CommentsCache({ request: (_path, options) => { calls++; fetchSignal = options!.signal!; return new Promise(r => { resolve = r; }) as any; } });
  const warm = new AbortController(), sheet = new AbortController();
  const first = cache.read('1', null, warm.signal); void first.catch(() => {}); warm.abort();
  const second = cache.read('1', null, sheet.signal); await tick(); assert.equal(calls, 1); assert.equal(fetchSignal.aborted, false);
  resolve(page); assert.equal((await second).items.length, 1); await assert.rejects(first);
  const pending = new AbortController(); const rejected = cache.read('2', null, pending.signal); pending.abort(); await assert.rejects(rejected); await tick(); assert.ok(fetchSignal.aborted); resolve(page); await tick(); assert.equal(cache.peek('2'), null);
});
test('comments keep playback but lock scroll; watch samples can suspend behind the sheet', () => {
  let confirmations = 0; const state = new FeedInteraction(() => {}, () => {}, () => confirmations++);
  state.observe('video', true); state.hold('edge'); state.hold('edge'); assert.equal(confirmations, 1);
  state.release(); state.hold('edge'); assert.equal(confirmations, 2); state.openComments();
  assert.deepEqual(interactionGates(state.state), { playbackBlocked: false, scrollBlocked: true });
  assert.equal(state.state.speed, 1); state.hold('edge'); assert.equal(confirmations, 2);
  const watch = new VisibleWatchTracker(); watch.sample(0, 0, true); watch.sample(1000, 1000, true);
  watch.sample(2000, 2000, !state.state.comments); watch.sample(3000, 3000, !state.state.comments); assert.equal(watch.totalMs, 1000);
  state.closeOverlay(); state.hold('center'); assert.equal(interactionGates(state.state).playbackBlocked, true);
  state.observe('next', true); assert.equal(state.state.speed, 1); state.dispose();
});
test('compact counts preserve real zero and unknown, without rounding across a unit', () => {
  assert.equal(compactCount(null), null); assert.equal(compactCount(undefined), null); assert.equal(compactCount(-1), null); assert.equal(compactCount(NaN), null);
  assert.equal(compactCount(0), '0'); assert.equal(compactCount(33000), '33k'); assert.equal(compactCount(1250), '1.2k'); assert.equal(compactCount(999999), '999.9k'); assert.equal(compactCount(1200000), '1.2m');
});

import { MediaCachePolicy } from '../src/lib/playback/MediaCachePolicy';
import { BufferedPlayerController } from '../src/lib/playback/BufferedPlayerController';
test('native disk cache survives same authenticated scope, clears on account/API/logout, fails closed', async () => {
  let owner: string | null = 'api:alice'; let clears = 0; let fail = false;
  const policy = new MediaCachePolicy({ configure: async bytes => { assert.equal(bytes, 128 * 1024 * 1024); }, readOwner: async () => owner, writeOwner: async value => { owner = value; }, clear: async () => { if (fail) throw new Error('busy'); clears++; } });
  assert.equal(await policy.prepare('api:alice'), true); assert.equal(clears, 0);
  assert.equal(await policy.prepare('api:bob'), true); assert.equal(clears, 1);
  assert.equal(await policy.prepare('other-api:bob'), true); assert.equal(clears, 2);
  assert.equal(await policy.prepare(null), false); assert.equal(owner, null); assert.equal(clears, 3);
  fail = true; assert.equal(await policy.prepare('api:alice'), false); assert.equal(owner, null);
});
test('distant warmer never replaces active/next buffer and ready next promotion needs no reload', async () => {
  const replacements: string[][] = [[], []]; const playing = [false, false];
  const controller = new BufferedPlayerController([0, 1].map(i => ({ replaceAsync: async (uri: string) => { replacements[i].push(uri); }, play: () => { playing[i] = true; }, pause: () => { playing[i] = false; } })) as any, () => {});
  await controller.setSelection(asset(0).url); controller.preload(asset(1).url); await tick();
  const before = replacements.flat().length;
  const warmed: string[] = []; const queue = new MediaWarmup({ warm: async uri => { warmed.push(uri); }, stop() {} });
  queue.update([asset(2), asset(3), asset(4)], true); await tick();
  assert.equal(warmed.length, 3); assert.equal(replacements.flat().length, before);
  await controller.setSelection(asset(1).url); assert.equal(replacements.flat().length, before); assert.equal(playing.filter(Boolean).length, 1);
  queue.dispose(); controller.dispose();
});
