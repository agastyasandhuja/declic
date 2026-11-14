import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import type { AddressInfo } from 'node:net';
const { previewApiProxy } = require('../scripts/preview-api-proxy.cjs');

test('preview transport forwards only app auth to loopback and rejects cookies, unknown mutations and redirects', async () => {
  let calls = 0;
  const upstream = createServer((request, response) => {
    calls++; assert.equal(request.headers.cookie, undefined); assert.equal(request.headers.authorization, 'Bearer synthetic');
    if (request.url === '/v1/me') { response.writeHead(302, { Location: 'https://other.example.test' }); response.end(); }
    else { response.setHeader('content-type', 'application/json'); response.setHeader('Retry-After', '2'); response.setHeader('Set-Cookie', 'never-forward=secret'); response.end('{"items":[]}'); }
  });
  await new Promise<void>(resolve => upstream.listen(0, '127.0.0.1', resolve));
  const proxy = createServer(previewApiProxy((_request: unknown, response: any) => { response.writeHead(404); response.end(); }, (upstream.address() as AddressInfo).port));
  await new Promise<void>(resolve => proxy.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${(proxy.address() as AddressInfo).port}`;
  try {
    const headers = { Authorization: 'Bearer synthetic', Cookie: 'provider-cookie=DO_NOT_FORWARD' };
    const feed = await fetch(`${origin}/v1/entertainment/feed`, { headers }); assert.equal(feed.status, 200); assert.equal(feed.headers.get('cache-control'), 'no-store');
    assert.equal(feed.headers.get('retry-after'), '2'); assert.equal(feed.headers.get('set-cookie'), null);
    assert.equal((await fetch(`${origin}/v1/me`, { headers })).status, 503);
    assert.equal((await fetch(`${origin}/v1/me`, { headers, method: 'POST' })).status, 405);
    assert.equal((await fetch(`${origin}/v1/admin`, { headers })).status, 404);
    assert.equal((await fetch(`${origin}/v1/feed/sessions`, { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'session-test' }, body: '{}' })).status, 200);
    assert.equal((await fetch(`${origin}/v1/feed/sessions`, { method: 'POST', body: '{}' })).status, 401);
    assert.equal((await fetch(`${origin}/v1/instagram/browser-session`, { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: '{"username":"demo","session_id":"synthetic"}' })).status, 200);
    assert.equal((await fetch(`${origin}/v1/instagram/browser-session`, { method: 'POST', body: '{}' })).status, 401);
    assert.equal((await fetch(`${origin}/v1/instagram/browser-session`, { headers })).status, 405);
    assert.equal((await fetch(`${origin}/v1/canvas/token`, { method: 'POST', headers, body: 'x'.repeat(70000) })).status, 413);
    assert.equal(calls, 4);
  } finally { await Promise.all([new Promise<void>(resolve => proxy.close(() => resolve())), new Promise<void>(resolve => upstream.close(() => resolve()))]); }
});
