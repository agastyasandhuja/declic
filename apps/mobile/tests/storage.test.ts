import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createChunkedStorage } from '../src/lib/auth/chunkedStorage';

function storage() {
  const values = new Map<string, string>(); let sequence = 0; let failOn: string | null = null;
  const adapter = createChunkedStorage({ getItem: async key => values.get(key) ?? null, setItem: async (key, value) => { if (key === failOn) throw new Error('storage full'); values.set(key, value); }, removeItem: async key => { values.delete(key); } }, () => `revision-${++sequence}`);
  return { values, adapter, fail: (key: string) => { failOn = key; } };
}
test('large Unicode sessions survive a new adapter and are erased on logout', async () => {
  const { values, adapter } = storage(); const session = '🌿'.repeat(3500);
  await adapter.setItem('auth', session);
  for (const value of values.values()) assert.ok(Buffer.byteLength(value) < 2048);
  const restarted = createChunkedStorage({ getItem: async key => values.get(key) ?? null, setItem: async (key, value) => { values.set(key, value); }, removeItem: async key => { values.delete(key); } }, () => 'restart');
  assert.equal(await restarted.getItem('auth'), session);
  await restarted.removeItem('auth'); assert.equal(await restarted.getItem('auth'), null); assert.equal(values.size, 0);
});
test('partial writes preserve the prior session and clean staged fragments', async () => {
  const { adapter, values, fail } = storage(); await adapter.setItem('auth', 'valid session');
  fail('auth.revision-2.1'); await assert.rejects(adapter.setItem('auth', 'x'.repeat(900)));
  assert.equal(await adapter.getItem('auth'), 'valid session'); assert.ok([...values.keys()].every(key => !key.includes('revision-2')));
});
test('incomplete sessions fail explicitly and can be cleared', async () => {
  const { adapter, values } = storage(); await adapter.setItem('auth', 'x'.repeat(500)); values.delete('auth.revision-1.1');
  await assert.rejects(adapter.getItem('auth'), /incomplete/); await adapter.removeItem('auth'); assert.equal(values.size, 0);
});
