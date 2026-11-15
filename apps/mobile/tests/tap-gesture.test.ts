import test from 'node:test';
import assert from 'node:assert/strict';
import { TapGesture, DOUBLE_TAP_MS } from '../src/lib/playback/TapGesture';

function fakeClock() {
  let timers: { at: number; run: () => void; id: number }[] = []; let now = 0; let id = 0;
  return {
    schedule: (run: () => void, ms: number) => { timers.push({ at: now + ms, run, id: ++id }); return id; },
    cancel: (handle: unknown) => { timers = timers.filter(timer => timer.id !== handle); },
    advance(ms: number) { now += ms; const due = timers.filter(timer => timer.at <= now); timers = timers.filter(timer => timer.at > now); due.forEach(timer => timer.run()); },
    get now() { return now; },
  };
}

test('one tap pauses only after the double-tap window closes', () => {
  const clock = fakeClock(); let singles = 0; let doubles = 0;
  const taps = new TapGesture(() => singles++, () => doubles++, clock.schedule, clock.cancel);
  taps.tap(100, 200, clock.now);
  clock.advance(DOUBLE_TAP_MS - 1); assert.equal(singles, 0);
  clock.advance(1); assert.equal(singles, 1); assert.equal(doubles, 0);
});

test('a double tap clicks at the tap point and never toggles playback', () => {
  const clock = fakeClock(); let singles = 0; const points: [number, number][] = [];
  const taps = new TapGesture(() => singles++, (x, y) => points.push([x, y]), clock.schedule, clock.cancel);
  taps.tap(100, 200, clock.now); clock.advance(120);
  assert.equal(taps.tap(110, 205, clock.now), 'double');
  clock.advance(1000);
  assert.equal(singles, 0); assert.deepEqual(points, [[110, 205]]);
  // A third quick tap starts a fresh sequence instead of chaining another click.
  taps.tap(110, 205, clock.now); clock.advance(DOUBLE_TAP_MS); assert.equal(singles, 1);
});

test('far-apart or slow taps stay single taps, and reset drops a pending tap', () => {
  const clock = fakeClock(); let singles = 0; let doubles = 0;
  const taps = new TapGesture(() => singles++, () => doubles++, clock.schedule, clock.cancel);
  taps.tap(20, 200, clock.now); clock.advance(100); taps.tap(300, 200, clock.now); clock.advance(DOUBLE_TAP_MS);
  assert.equal(doubles, 0); assert.equal(singles, 1);
  taps.tap(20, 200, clock.now); clock.advance(DOUBLE_TAP_MS + 50); taps.tap(20, 200, clock.now); clock.advance(DOUBLE_TAP_MS);
  assert.equal(doubles, 0); assert.equal(singles, 3);
  taps.tap(20, 200, clock.now); taps.reset(); clock.advance(DOUBLE_TAP_MS);
  assert.equal(singles, 3);
});
