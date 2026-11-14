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
