import test from 'node:test';
import assert from 'node:assert/strict';
import { FeedBootstrap } from '../src/features/feed/FeedBootstrap';
import { unifiedFeedQuery } from '../src/features/feed/paging';
import type { ApiClient } from '../src/lib/api/client';
const tick = () => new Promise<void>(resolve => setImmediate(resolve));
const quiz = { item_id: 'occurrence', kind: 'quiz', quiz: { quiz_instance_id: 'quiz', prompt: 'Why?', options: [{ option_id: 'a', text: 'A' }, { option_id: 'b', text: 'B' }] } };
const page = { session_id: 'fresh-session', recommendation_revision: 9, next_cursor: 'fresh-cursor', items: [quiz] };
test('eager startup and mounted feed share one fresh page with matching cursor size and unchanged quiz gate', async () => {
  let requests = 0, authorized = 0; let complete!: (value: unknown) => void;
  const api: ApiClient = { async request(path, options) {
    requests++; assert.equal(path, '/v1/feed/bootstrap');
    assert.deepEqual(options?.body, { limit: Number(unifiedFeedQuery('session', null).get('limit')), preferred_video_ids: ['cached'] });
    assert.ok(options?.headers); return await new Promise(resolve => { complete = resolve; }) as any;
  } };
  const startup = new FeedBootstrap({ preferred: async () => ['cached'], authorize: async (_scope, value) => { assert.equal(value.items[0].kind, 'quiz'); authorized++; }, requestId: () => 'request' });
  startup.begin('api:alice', api); await tick(); assert.equal(requests, 1);
  const result = startup.take('api:alice', api); complete(page);
  assert.deepEqual(await result, page); assert.equal(requests, 1); assert.equal(authorized, 1);
});
test('logout/account/API replacement aborts startup and never authorizes its late response', async () => {
  let complete!: (value: unknown) => void, authorized = 0; let signal: AbortSignal | undefined;
  const api: ApiClient = { request: async (_path, options) => { signal = options?.signal as AbortSignal; return await new Promise(resolve => { complete = resolve; }) as any; } };
  const startup = new FeedBootstrap({ preferred: async () => [], authorize: async () => { authorized++; }, requestId: () => 'request' });
  const old = startup.take('api:alice', api); await tick(); startup.cancel();
  assert.equal(signal?.aborted, true); complete(page); await assert.rejects(old, /startup changed/); assert.equal(authorized, 0);
});
test('failed fresh request is retryable and optional hint failures never block fresh feed', async () => {
  let calls = 0;
  const api: ApiClient = { request: async (_path, options) => { assert.deepEqual((options?.body as any).preferred_video_ids, []); if (++calls === 1) throw new Error('offline'); return page as any; } };
  const startup = new FeedBootstrap({ preferred: async () => { throw new Error('storage unavailable'); }, authorize: async () => { throw new Error('cache unavailable'); }, requestId: () => 'request' });
  await assert.rejects(startup.take('api:alice', api), /offline/);
  assert.deepEqual(await startup.take('api:alice', api), page); assert.equal(calls, 2);
});

test('stale bootstrap gets one new idempotency key, never an unbounded refresh loop', async () => {
  const { ApiError } = await import('../src/lib/api/client'); let count = 0; const keys: string[] = [];
  const api: ApiClient = { request: async (_path, options) => { keys.push((options?.headers as any)['Idempotency-Key']); if (++count < 3) throw new ApiError('stale', 409, 'STALE_BOOTSTRAP', false); return page as any; } };
  let key = 0; const startup = new FeedBootstrap({ preferred: async () => [], authorize: async () => {}, requestId: () => String(++key) });
  await assert.rejects(startup.take('api:alice', api), /stale/); assert.deepEqual(keys, ['1', '2']);
  assert.deepEqual(await startup.take('api:alice', api), page);
});
