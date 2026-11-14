import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, createApiClient } from '../src/lib/api/client';

test('only the session token is attached and one refresh retries a protected read', async () => {
  const tokens: string[] = []; let refreshes = 0;
  const api = createApiClient({ baseUrl: 'https://api.example.test', getAccessToken: async force => { if (force) refreshes++; return force ? 'fresh' : 'expired'; }, onUnauthorized() { assert.fail('valid refresh'); }, fetcher: async (_url, options) => {
    const token = new Headers(options?.headers).get('Authorization')!; tokens.push(token);
    return token === 'Bearer expired' ? new Response('{}', { status: 401 }) : Response.json({ accepted: true });
  } });
  const result = await api.request('/v1/me', { headers: { Authorization: 'Bearer forged' } });
  assert.deepEqual(result, { accepted: true }); assert.deepEqual(tokens, ['Bearer expired', 'Bearer fresh']); assert.equal(refreshes, 1);
});
test('failed refresh expires the session without looping', async () => {
  let requests = 0; let expired = 0;
  const api = createApiClient({ baseUrl: 'https://api.example.test', getAccessToken: async force => force ? null : 'old', onUnauthorized: () => expired++, fetcher: async () => { requests++; return new Response('{}', { status: 401 }); } });
  await assert.rejects(api.request('/v1/me'), (error: ApiError) => error.status === 401);
  assert.equal(requests, 1); assert.equal(expired, 1);
});
test('preview, foreign URLs and insecure origins never receive credentials', async () => {
  let requests = 0; const fetcher: typeof fetch = async () => { requests++; return Response.json({}); };
  const options = { baseUrl: 'https://api.example.test', getAccessToken: async () => null, onUnauthorized() {}, fetcher };
  await assert.rejects(createApiClient(options).request('/v1/me'), (error: ApiError) => error.code === 'AUTH_REQUIRED');
  await assert.rejects(createApiClient({ ...options, getAccessToken: async () => 'token' }).request('https://other.example.test/v1/me'), (error: ApiError) => error.code === 'INVALID_API_PATH');
  await assert.rejects(createApiClient({ ...options, baseUrl: 'http://localhost:8000' }).request('/v1/me'), (error: ApiError) => error.code === 'INVALID_API_ORIGIN');
  assert.equal(requests, 0);
});
test('only idempotent mutations can be replayed after refresh', async () => {
  let requests = 0; const api = createApiClient({ baseUrl: 'https://api.example.test', getAccessToken: async force => force ? 'fresh' : 'old', onUnauthorized() { assert.fail('A successful refresh must preserve the session.'); }, fetcher: async (_url, options) => { requests++; return new Headers(options?.headers).get('Authorization') === 'Bearer fresh' ? Response.json({ ok: true }) : new Response('{}', { status: 401 }); } });
  await assert.rejects(api.request('/v1/quizzes/demo/answers', { method: 'POST', body: { selected_option_id: 'a' } })); assert.equal(requests, 1);
  const result = await api.request('/v1/quizzes/demo/answers', { method: 'POST', headers: { 'Idempotency-Key': 'attempt-demo' }, body: { selected_option_id: 'a' } });
  assert.deepEqual(result, { ok: true }); assert.equal(requests, 3);
});
test('timeouts are retryable and do not leave callers waiting', async () => {
  const api = createApiClient({ baseUrl: 'https://api.example.test', timeoutMs: 5, getAccessToken: async () => 'token', onUnauthorized() {}, fetcher: async (_url, options) => new Promise((_resolve, reject) => options?.signal?.addEventListener('abort', () => reject(new Error('aborted')))) });
  await assert.rejects(api.request('/v1/me'), (error: ApiError) => error.code === 'NETWORK_ERROR' && error.retryable);
});
