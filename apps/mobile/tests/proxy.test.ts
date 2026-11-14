import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import type { AddressInfo } from 'node:net';
const { previewApiProxy } = require('../scripts/preview-api-proxy.cjs');

test('preview transport forwards only app auth to loopback and rejects cookies, mutations and redirects', async () => {
  let calls = 0;
  const upstream = createServer((request, response) => {
    calls++; assert.equal(request.headers.cookie, undefined); assert.equal(request.headers.authorization, 'Bearer synthetic');
    if (request.url === '/v1/me') { response.writeHead(302, { Location: 'https://other.example.test' }); response.end(); }
    else { response.setHeader('content-type', 'application/json'); response.end('{"items":[]}'); }
  });
  await new Promise<void>(resolve => upstream.listen(0, '127.0.0.1', resolve));
  const proxy = createServer(previewApiProxy((_request: unknown, response: any) => { response.writeHead(404); response.end(); }, (upstream.address() as AddressInfo).port));
  await new Promise<void>(resolve => proxy.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${(proxy.address() as AddressInfo).port}`;
  try {
    const headers = { Authorization: 'Bearer synthetic', Cookie: 'provider-cookie=DO_NOT_FORWARD' };
    const feed = await fetch(`${origin}/v1/entertainment/feed`, { headers }); assert.equal(feed.status, 200); assert.equal(feed.headers.get('cache-control'), 'no-store');
    assert.equal((await fetch(`${origin}/v1/me`, { headers })).status, 503);
    assert.equal((await fetch(`${origin}/v1/me`, { headers, method: 'POST' })).status, 405);
    assert.equal((await fetch(`${origin}/v1/admin`, { headers })).status, 404);
    assert.equal(calls, 2);
  } finally { await Promise.all([new Promise<void>(resolve => proxy.close(() => resolve())), new Promise<void>(resolve => upstream.close(() => resolve()))]); }
});
