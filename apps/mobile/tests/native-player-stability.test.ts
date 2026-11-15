import test from 'node:test';
import assert from 'node:assert/strict';
import { createExpoPlayerDriver } from '../src/lib/playback/ExpoPlayerDriver';
import { BufferedPlayerController } from '../src/lib/playback/BufferedPlayerController';
import { DecodedFrames } from '../src/lib/playback/DecodedFrames';
const tick = () => new Promise<void>(resolve => setImmediate(resolve));
function nativePlayer() {
  const listeners = new Map<string, Set<(data: any) => void>>();
  const sources: any[] = []; let muted = true, rate = 1; const writes = { mute: 0, rate: 0 };
  const player = {
    status: 'readyToPlay', playing: false, currentTime: 0,
    get muted() { return muted; }, set muted(value: boolean) { writes.mute++; muted = value; },
    get playbackRate() { return rate; }, set playbackRate(value: number) { writes.rate++; rate = value; player.playing = true; },
    play() { player.playing = true; }, pause() { player.playing = false; },
    async replaceAsync(value: unknown) { sources.push(value); },
    addListener(name: string, callback: (data: any) => void) {
      if (!listeners.has(name)) listeners.set(name, new Set()); listeners.get(name)!.add(callback);
      return { remove() { listeners.get(name)!.delete(callback); } };
    },
  };
  return { player, writes, sources, listeners, emit(name: string, data: any) { for (const callback of [...listeners.get(name) ?? []]) callback(data); } };
}
test('resolved replacement is not ready until its actual source and native readiness match', async () => {
  const native = nativePlayer(); const driver = createExpoPlayerDriver(native.player as any, async uri => ({ uri }));
  let ready = false; const loaded = driver.replaceAsync('https://example.test/next.mp4').then(() => { ready = true; });
  await tick(); assert.equal(ready, false); // Old item was ready, replaceAsync already resolved.
  native.emit('sourceChange', { source: { uri: 'https://example.test/old.mp4' } }); native.emit('statusChange', {}); await tick(); assert.equal(ready, false);
  native.player.status = 'loading'; native.emit('sourceChange', { source: { uri: 'https://example.test/next.mp4' } }); await tick(); assert.equal(ready, false);
  native.player.status = 'readyToPlay'; native.emit('statusChange', {}); await loaded; assert.equal(ready, true);
  assert.equal([...native.listeners.values()].reduce((n, callbacks) => n + callbacks.size, 0), 0);
});
test('failed local file has exactly one direct network fallback and no cache retry loop', async () => {
  const native = nativePlayer(); const discarded: string[] = [];
  const driver = createExpoPlayerDriver(native.player as any, async () => ({ uri: 'file:///cache/video.mp4' }), uri => { discarded.push(uri); });
  const remote = 'https://example.test/clip.mp4'; const loading = driver.replaceAsync(remote);
  await tick(); native.player.status = 'error'; native.emit('sourceChange', { source: { uri: 'file:///cache/video.mp4' } }); await tick();
  assert.deepEqual(discarded, [remote]); assert.deepEqual(native.sources, [{ uri: 'file:///cache/video.mp4' }, { uri: remote, useCaching: false }]);
  native.player.status = 'readyToPlay'; native.emit('sourceChange', { source: { uri: remote } }); await loading;
});
test('native mute and rate no-ops do not reconfigure audio or start a paused player', () => {
  const native = nativePlayer(); const driver = createExpoPlayerDriver(native.player as any, uri => ({ uri }));
  driver.setMuted!(true); driver.setRate!(1); assert.deepEqual(native.writes, { mute: 0, rate: 0 }); assert.equal(native.player.playing, false);
  driver.setMuted!(false); driver.setMuted!(false); driver.setRate!(2); driver.setRate!(2); assert.deepEqual(native.writes, { mute: 1, rate: 1 });
});
test('standby completion and repeated gates do not replay, mute or pause the active player', async () => {
  const counts = [0, 1].map(() => ({ play: 0, pause: 0, mute: 0, rate: 0 })); let active = 0;
  const drivers = counts.map(count => ({ play() { count.play++; }, pause() { count.pause++; }, setMuted() { count.mute++; }, setRate() { count.rate++; }, async replaceAsync() {} })) as any;
  const controller = new BufferedPlayerController(drivers, state => { active = state.activeSlot; });
  await controller.setSelection('one'); const before = { ...counts[active] };
  controller.preload('two'); await tick();
  for (let i = 0; i < 100; i++) { controller.setGate({}); controller.setRate(1); controller.setMuted(false); }
  assert.deepEqual(counts[active], before);
  const next = 1 - active; const nextBefore = { ...counts[next] };
  await controller.setSelection('two'); assert.equal(counts[next].play, nextBefore.play + 1);
  controller.dispose();
});
test('decoded standby frame survives promotion, but old generation/retry callbacks cannot grant credit', () => {
  const frames = new DecodedFrames();
  frames.observe([{ generation: 1, ready: true }, { generation: 2, ready: true }]);
  assert.equal(frames.mark(1, 2), true); assert.equal(frames.has(1), true);
  // Role change doesn't change physical source identity or need another first frame.
  frames.observe([{ generation: 1, ready: true }, { generation: 2, ready: true }]); assert.equal(frames.has(1), true);
  frames.observe([{ generation: 1, ready: true }, { generation: 3, ready: false }]); assert.equal(frames.has(1), false); assert.equal(frames.mark(1, 2), false);
  frames.observe([{ generation: 1, ready: true }, { generation: 3, ready: true }]); assert.equal(frames.has(1), false); assert.equal(frames.mark(1, 2), false); assert.equal(frames.mark(1, 3), true);
});

test('driver pins current local file until replacement readiness and releases pending/current holds on disposal', async () => {
  const native = nativePlayer(), released: string[] = [];
  const driver = createExpoPlayerDriver(native.player as any, async uri => ({ uri: `file:///cache/${uri}.mp4` }), undefined, uri => { released.push(uri); });
  const first = driver.replaceAsync('one'); await tick(); native.emit('sourceChange', { source: { uri: 'file:///cache/one.mp4' } }); await first;
  const second = driver.replaceAsync('two'); await tick(); assert.deepEqual(released, []);
  native.emit('sourceChange', { source: { uri: 'file:///cache/two.mp4' } }); await second; assert.deepEqual(released, ['one']);
  const third = driver.replaceAsync('three'); void third.catch(() => {}); await tick(); driver.dispose!(); await assert.rejects(third); await tick();
  assert.deepEqual(released.sort(), ['one', 'three', 'two']);
  assert.equal([...native.listeners.values()].reduce((n, callbacks) => n + callbacks.size, 0), 0);
});
test('an async file lookup finishing after player disposal releases its retain without touching native media', async () => {
  const native = nativePlayer(), released: string[] = []; let resolve!: (value: any) => void;
  const driver = createExpoPlayerDriver(native.player as any, () => new Promise(r => { resolve = r; }), undefined, uri => { released.push(uri); });
  const loading = driver.replaceAsync('late'); driver.dispose!(); resolve({ uri: 'file:///cache/late.mp4' }); await assert.rejects(loading);
  assert.deepEqual(released, ['late']); assert.equal(native.sources.length, 0);
});
