import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SinglePlayerController } from '../src/lib/playback/SinglePlayerController';

test('a load finishing in the background cannot restart audio; returning resumes it', async () => {
  let finish!: () => void; const actions: string[] = [];
  const controller = new SinglePlayerController({ play: () => actions.push('play'), pause: () => actions.push('pause'), replaceAsync: () => new Promise<void>(resolve => { finish = resolve; }) }, () => {});
  const load = controller.setSource('one'); await Promise.resolve(); await Promise.resolve();
  controller.setGate({ foreground: false }); finish(); await load;
  assert.equal(actions.includes('play'), false);
  controller.setGate({ foreground: true }); assert.equal(actions.at(-1), 'play');
  controller.setGate({ focused: false }); assert.equal(actions.at(-1), 'pause');
  controller.setGate({ manuallyPaused: true, focused: true }); assert.equal(actions.at(-1), 'pause');
  controller.dispose();
});
test('rapid swipes serialize replacements and never play a stale source', async () => {
  let finish!: () => void; const replacements: string[] = []; const played: string[] = []; let current = '';
  const controller = new SinglePlayerController({ play: () => played.push(current), pause() {}, replaceAsync: async uri => {
    replacements.push(uri); if (uri === 'one') await new Promise<void>(resolve => { finish = resolve; }); current = uri;
  } }, () => {});
  const first = controller.setSource('one'); await Promise.resolve(); await Promise.resolve();
  controller.setSource('two'); const last = controller.setSource('three'); finish(); await first; await last;
  assert.deepEqual(replacements, ['one', 'three']); assert.deepEqual(played, ['three']);
});
test('failed playback can recover on retry and disposal silences pending work', async () => {
  let fails = true; let plays = 0; let latestError: string | null = null;
  const controller = new SinglePlayerController({ play: () => plays++, pause() {}, replaceAsync: async () => { if (fails) throw new Error('network'); } }, state => { latestError = state.error; });
  await controller.setSource('clip'); assert.ok(latestError); assert.equal(plays, 0);
  fails = false; await controller.setSource('clip'); assert.equal(latestError, null); assert.equal(plays, 1);
  controller.dispose(); await controller.setSource('another'); assert.equal(plays, 1);
});

import { BufferedPlayerController, type BufferedPlaybackState } from '../src/lib/playback/BufferedPlayerController';
import { VisibleWatchTracker } from '../src/lib/playback/VisibleWatchTracker';
test('the next media buffer is paused and reused; navigation and background silence both slots', async () => {
  const playing = [false, false]; const sources = ['', '']; const loads: string[] = [];
  const drivers = [0, 1].map(slot => ({ play() { playing[slot] = true; assert.ok(playing.filter(Boolean).length <= 1); }, pause() { playing[slot] = false; }, async replaceAsync(uri: string) { sources[slot] = uri; loads.push(uri); } })) as any;
  const states: BufferedPlaybackState[] = [];
  const controller = new BufferedPlayerController(drivers, state => states.push(state));
  await controller.setSelection('one', 'two'); await Promise.resolve(); await Promise.resolve();
  assert.equal(playing.filter(Boolean).length, 1);
  states.length = 0;
  await controller.setSelection('two', 'three'); await Promise.resolve(); await Promise.resolve();
  assert.ok(states.length > 0);
  assert.equal(states.some(state => state.loading), false, 'a ready preload must not flash a loading state');
  assert.equal(loads.filter(uri => uri === 'two').length, 1);
  assert.equal(sources[playing.findIndex(Boolean)], 'two');
  controller.setGate({ foreground: false }); assert.deepEqual(playing, [false, false]);
  controller.setGate({ foreground: true, focused: false }); assert.deepEqual(playing, [false, false]);
  controller.setGate({ focused: true }); assert.equal(playing.filter(Boolean).length, 1);
  controller.dispose(); assert.deepEqual(playing, [false, false]);
});
test('rapid selections and a slow stale preload cannot start a second player', async () => {
  let finish!: () => void; const playing = [false, false]; const played: string[] = []; const source = ['', ''];
  const drivers = [0, 1].map(slot => ({ play() { playing[slot] = true; played.push(source[slot]); assert.ok(playing.filter(Boolean).length <= 1); }, pause() { playing[slot] = false; }, async replaceAsync(uri: string) { if (uri === 'two') await new Promise<void>(resolve => { finish = resolve; }); source[slot] = uri; } })) as any;
  const controller = new BufferedPlayerController(drivers, () => {});
  await controller.setSelection('one', 'two'); await Promise.resolve(); await Promise.resolve();
  const second = controller.setSelection('two'); const third = controller.setSelection('three');
  controller.setGate({ foreground: false }); finish(); await second; await third;
  assert.deepEqual(playing, [false, false]); assert.ok(!played.includes('two'));
  controller.dispose();
});
test('a stuck source produces bounded recovery UI without granting playback', async () => {
  let state: BufferedPlaybackState | undefined;
  const driver = { play() { assert.fail('stuck source'); }, pause() {}, replaceAsync: () => new Promise<void>(() => {}) };
  const controller = new BufferedPlayerController([driver, driver], value => { state = value; }, 5);
  void controller.setSelection('stuck');
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.ok(state?.timedOut); assert.equal(state?.ready, false); controller.dispose();
});
test('watch observations exclude buffering, background, seeks and long sample gaps, and include loops', () => {
  const watch = new VisibleWatchTracker();
  watch.sample(0, 0, true, 1000); watch.sample(500, 500, true, 1000);
  watch.sample(500, 1000, true, 1000); assert.equal(watch.totalMs, 500);
  watch.sample(900, 1500, false, 1000); watch.sample(900, 5000, true, 1000);
  watch.sample(100, 5200, true, 1000); assert.equal(watch.totalMs, 700);
  watch.sample(30000, 5700, true, 40000); assert.equal(watch.totalMs, 700);
  watch.sample(30500, 9000, true, 40000); assert.equal(watch.totalMs, 700);
});

import { PlaybackStallGuard } from '../src/lib/playback/VisibleWatchTracker';
test('post-load stalls time out while manual pause/background reset the watchdog', () => {
  const stall = new PlaybackStallGuard(1000);
  assert.equal(stall.sample(0, 0, true), false);
  assert.equal(stall.sample(500, 500, true), false);
  assert.equal(stall.sample(500, 1500, true), true);
  assert.equal(stall.sample(500, 9000, false), false);
  assert.equal(stall.sample(500, 9500, true), false);
  assert.equal(stall.sample(1000, 10000, true), false);
});

import { FirstFrameGuard } from '../src/lib/playback/VisibleWatchTracker';
test('audio-only playback times out without a rendered frame; selection and background reset the deadline', () => {
  const guard = new FirstFrameGuard(1000);
  assert.equal(guard.sample(1, false, 0, true), false);
  // Native playback/status events may keep arriving while audio advances.
  assert.equal(guard.sample(1, false, 500, true), false);
  assert.equal(guard.sample(1, false, 1000, true), true);
  assert.equal(guard.sample(1, true, 1500, true), false);
  assert.equal(guard.sample(2, false, 2000, true), false);
  assert.equal(guard.sample(2, false, 2500, false), false);
  assert.equal(guard.sample(2, false, 9000, true), false);
  assert.equal(guard.sample(2, false, 10000, true), true);
});

test('source readiness identifies the selected URI and surface generation across preload promotion and retry', async () => {
  let state!: BufferedPlaybackState;
  const driver = { play() {}, pause() {}, async replaceAsync() {} };
  const controller = new BufferedPlayerController([driver, driver], value => { state = value; });
  await controller.setSelection('one', 'two');
  const first = state.selection;
  assert.equal(state.sourceUri, 'one');
  await controller.setSelection('two');
  assert.equal(state.sourceUri, 'two');
  assert.ok(state.selection > first);
  const promoted = state.selection;
  await controller.setSelection('two', undefined, true);
  assert.ok(state.selection > promoted);
  assert.equal(state.ready, true);
  controller.dispose();
});

test('late visibility/error callbacks and repeated cleanup never touch released native drivers', async () => {
  let released = false;
  const driver = { play() { assert.equal(released, false); }, pause() { assert.equal(released, false); }, async replaceAsync() { assert.equal(released, false); } };
  const controller = new BufferedPlayerController([driver, driver], () => {});
  controller.dispose(); released = true;
  controller.setGate({ foreground: true }); controller.reportError(); controller.preload('late'); controller.dispose();
  await controller.setSelection('late');
});

test('a stalled stale preload cannot block a newer clip on the free slot', async () => {
  let release!: () => void;
  const source = ['', '']; const playing = [false, false]; const replacements: string[] = [];
  const driver = (slot: number) => ({
    pause() { playing[slot] = false; },
    play() { playing[slot] = true; assert.equal(playing.filter(Boolean).length, 1); },
    async replaceAsync(uri: string) {
      replacements.push(uri);
      if (uri === 'slow-preload') await new Promise<void>(resolve => { release = resolve; });
      source[slot] = uri;
    },
  });
  const controller = new BufferedPlayerController([driver(0), driver(1)], () => {});
  await controller.setSelection('first', 'slow-preload'); await Promise.resolve(); await Promise.resolve();
  await controller.setSelection('new-selection');
  assert.equal(source[playing.findIndex(Boolean)], 'new-selection', 'must play before slow preload resolves');
  controller.setGate({ foreground: false });
  release(); await Promise.resolve(); await Promise.resolve();
  assert.deepEqual(playing, [false, false]);
  assert.deepEqual(replacements, ['first', 'slow-preload', 'new-selection']);
  controller.dispose();
});

test('adjacent buffer readiness is published without granting its audio or resetting the active selection', async () => {
  let state!: BufferedPlaybackState; const playing = [false, false];
  const drivers = [0, 1].map(slot => ({ play() { playing[slot] = true; assert.ok(playing.filter(Boolean).length <= 1); }, pause() { playing[slot] = false; }, async replaceAsync() {} })) as any;
  const controller = new BufferedPlayerController(drivers, value => { state = value; });
  await controller.setSelection('one'); const selection = state.selection;
  controller.preload('two'); await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
  assert.equal(state.selection, selection); assert.equal(state.sourceUri, 'one');
  assert.deepEqual(state.buffers?.[1 - state.activeSlot], { uri: 'two', ready: true });
  assert.equal(playing[1 - state.activeSlot], false);
  await controller.setSelection('two');
  assert.deepEqual(state.buffers?.[1 - state.activeSlot], { uri: 'one', ready: true });
  assert.equal(playing[1 - state.activeSlot], false);
  controller.dispose();
});
