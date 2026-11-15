import test from 'node:test';
import assert from 'node:assert/strict';
import { StartupTrace, type StartupSnapshot } from '../src/lib/playback/StartupTrace';
test('startup diagnostics record only bounded first-source/frame timing and ignore later/background callbacks', async () => {
  let clock = 1000; const writes: StartupSnapshot[] = [];
  const trace = new StartupTrace(async value => { writes.push(value); }, () => clock);
  trace.start(); clock += 80; trace.page(); clock += 20; trace.source(true, true); clock += 30; trace.frame();
  trace.source(false, false); trace.frame(); trace.cancel(); trace.page(); trace.frame();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(writes.length, 4); assert.deepEqual(writes.at(-1), { schema_version: 1, started_at: new Date(1000).toISOString(), phase: 'frame', page_ms: 80, source_ms: 100, first_frame_ms: 130, cache_hit: true, starter_alias: true });
});
