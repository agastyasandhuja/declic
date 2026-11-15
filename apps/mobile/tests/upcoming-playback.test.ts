import test from 'node:test';
import assert from 'node:assert/strict';
import type { PlaybackSource } from '../src/contracts/generated';
import { prepareUpcomingPlayback, updateUpcomingPlayback } from '../src/features/feed/upcomingPlayback';
import { ApiError } from '../src/lib/api/client';
import { BufferedPlayerController } from '../src/lib/playback/BufferedPlayerController';

const playback = (id: string, expires_at: string | null = null): PlaybackSource => ({
  kind: 'mp4', asset_id: id, url: `https://example.test/${id}.mp4`, expires_at, mime_type: 'video/mp4',
});
const resolveMissing = async () => { throw new ApiError('Missing', 404, 'VIDEO_NOT_FOUND', false); };

test('a failed standby skips a missing clip and preloads its replacement for promotion', async () => {
  const loaded: string[] = [];
  const active = playback('active'), missing = playback('missing'), replacement = playback('replacement');
  const driver = {
    play() {}, pause() {},
    async replaceAsync(uri: string) {
      loaded.push(uri);
      if (uri === missing.url) throw new Error('CDN failed');
    },
  };
  const controller = new BufferedPlayerController([driver, driver], () => {});
  await controller.setSelection(active.url);
  const signal = new AbortController().signal;
  const update = await prepareUpcomingPlayback(missing, controller, resolveMissing, signal);
  assert.deepEqual(update, { kind: 'remove' });
  const gate = { kind: 'quiz' };
  const queue = [active, missing, replacement, gate];
  const updated = updateUpcomingPlayback(queue, 0, missing, update!, (_clip, source) => source);
  assert.deepEqual(updated, [active, replacement, gate]);
  assert.equal(await prepareUpcomingPlayback(replacement, controller, resolveMissing, signal), undefined);
  await controller.setSelection(replacement.url);
  assert.deepEqual(loaded, [active.url, missing.url, replacement.url]);
  controller.dispose();
});

test('stale standby links resolve before native load and a fresh link stays in the same slot', async () => {
  const expired = playback('old', new Date(Date.now() - 1000).toISOString());
  const fresh = playback('fresh');
  const controller = { preload: async () => assert.fail('expired media should not reach the player') };
  const update = await prepareUpcomingPlayback(expired, controller, async () => fresh, new AbortController().signal);
  assert.deepEqual(update, { kind: 'refresh', playback: fresh });
  assert.deepEqual(updateUpcomingPlayback([expired], -1, expired, update!, (_clip, source) => source), [fresh]);
});

test('transient errors and stale results cannot change the visible queue', async () => {
  const clip = playback('clip');
  const controller = { preload: async () => 'failed' as const };
  const abort = new AbortController();
  const busy = async () => { throw new ApiError('Busy', 503, 'INSTAGRAM_BUSY', true); };
  assert.equal(await prepareUpcomingPlayback(clip, controller, busy, abort.signal), undefined);
  const cancelled = async () => { abort.abort(); return resolveMissing(); };
  assert.equal(await prepareUpcomingPlayback(clip, controller, cancelled, abort.signal), undefined);
  const queue = [clip];
  assert.equal(updateUpcomingPlayback(queue, 0, clip, { kind: 'remove' }, (_clip, source) => source), queue);
  assert.equal(updateUpcomingPlayback(queue, -1, { ...clip }, { kind: 'remove' }, (_clip, source) => source), queue);
});
