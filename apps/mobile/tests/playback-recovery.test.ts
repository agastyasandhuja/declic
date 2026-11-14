import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PlaybackRecovery, needsPlaybackRefresh } from '../src/lib/playback/PlaybackRecovery';
import { BufferedPlayerController } from '../src/lib/playback/BufferedPlayerController';
import { VisibleWatchTracker } from '../src/lib/playback/VisibleWatchTracker';

test('foreground recovery detects expiry and a ten-second safety window without inventing expiry', () => {
  const now = Date.parse('2026-11-14T12:00:00Z');
  assert.equal(needsPlaybackRefresh(null, now), false);
  assert.equal(needsPlaybackRefresh('2026-11-14T12:01:00Z', now), false);
  assert.equal(needsPlaybackRefresh('2026-11-14T12:00:10Z', now), true);
  assert.equal(needsPlaybackRefresh('2026-11-14T11:59:00Z', now), true);
  assert.equal(needsPlaybackRefresh('invalid', now), true);
});

test('expiry, revoked-link, and black-frame callbacks share one renewal per visible visit', () => {
  const recovery = new PlaybackRecovery();
  recovery.observe('occurrence', true);
  assert.equal(recovery.claim('occurrence'), true);
  // A renewal failure, old status event, or first-frame deadline must not loop.
  recovery.observe('occurrence', true);
  assert.equal(recovery.claim('occurrence'), false);
  assert.equal(recovery.claim('occurrence'), false);
  recovery.observe('occurrence', false);
  assert.equal(recovery.claim('occurrence'), false);
  recovery.observe('occurrence', true);
  assert.equal(recovery.claim('occurrence'), true);
});

test('a quiz or another selected item cannot authorize renewal for a stale video callback', () => {
  const recovery = new PlaybackRecovery();
  recovery.observe('old-video', true);
  recovery.observe(null, true); // quiz has no video selection
  assert.equal(recovery.claim('old-video'), false);
  recovery.observe('next-video', true);
  assert.equal(recovery.claim('old-video'), false);
  assert.equal(recovery.claim('next-video'), true);
});

test('late renewal preserves background/manual gates and frame verification before more watch credit', async () => {
  const recovery = new PlaybackRecovery(); const playing = [false, false];
  const drivers = [0, 1].map(slot => ({ play() { playing[slot] = true; }, pause() { playing[slot] = false; }, async replaceAsync() {} })) as any;
  const controller = new BufferedPlayerController(drivers, () => {});
  const watch = new VisibleWatchTracker();
  await controller.setSelection('old-url');
  watch.sample(0, 0, true); watch.sample(500, 500, true);
  recovery.observe('video', true); assert.equal(recovery.claim('video'), true);
  controller.setGate({ focused: false }); watch.sample(500, 500, false);
  controller.setGate({ foreground: false }); recovery.observe('video', false);
  await controller.setSelection('renewed-url', undefined, true);
  controller.setGate({ focused: true }); // a late resolver result still cannot override foreground
  assert.deepEqual(playing, [false, false]);
  watch.sample(1000, 1000, false); assert.equal(watch.totalMs, 500);
  controller.setGate({ foreground: true, manuallyPaused: true });
  assert.deepEqual(playing, [false, false]);
  controller.setGate({ manuallyPaused: false });
  assert.equal(playing.filter(Boolean).length, 1);
  // New media starts at zero; old credit survives but no credit until a new frame.
  watch.sample(0, 1500, false); watch.sample(500, 2000, true);
  assert.equal(watch.totalMs, 500);
  watch.sample(1000, 2500, true); assert.equal(watch.totalMs, 1000);
  controller.dispose();
});

import { PlaybackSeek } from '../src/lib/playback/PlaybackRecovery';
test('renewal waits for one seek to the last observed position and cannot add watch credit during it', () => {
  const seek = new PlaybackSeek(); const watch = new VisibleWatchTracker();
  watch.sample(14500, 0, true); watch.sample(15000, 500, true);
  seek.capture('clip', 15000, 1);
  assert.equal(seek.anchor('clip', 0), 15000); // resume/start uses an actual prior observation
  assert.equal(seek.settled('clip', 0, 60000, 600), 'waiting');
  assert.equal(seek.takeTarget('foreign', 2, 600), null);
  assert.equal(seek.takeTarget('clip', 1, 600), null); // late frame from the old source
  assert.equal(seek.takeTarget('clip', 2, 600), 15000);
  assert.equal(seek.takeTarget('clip', 2, 700), null); // no repeated seeks per frame
  assert.equal(seek.settled('clip', 0, 60000, 1000), 'waiting');
  watch.sample(0, 1000, false); assert.equal(watch.totalMs, 500);
  assert.equal(seek.settled('clip', 15000, 60000, 1500), 'ready');
  watch.sample(15000, 1500, false); watch.sample(15500, 2000, true);
  assert.equal(watch.totalMs, 500); // seeking 15 seconds added no visible time
  watch.sample(16000, 2500, true); assert.equal(watch.totalMs, 1000);
  assert.equal(seek.anchor('clip', 16000), 16000); // subsequent server progress remains monotonic
});

test('a failed seek times out without losing its prior anchor on a manual retry', () => {
  const seek = new PlaybackSeek(); seek.capture('clip', 15000, 1); seek.takeTarget('clip', 2, 0);
  assert.equal(seek.settled('clip', 100, 60000, 5000), 'timeout');
  seek.capture('clip', 100, 2);
  assert.equal(seek.takeTarget('clip', 3, 6000), 15000);
  seek.clear(); assert.equal(seek.isPending('clip'), false);
});
