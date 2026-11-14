const http = require('node:http');
const { randomUUID } = require('node:crypto');

// Opt-in development transport only. Python verifies the app token and owner.
// No arbitrary destination, provider cookies, redirects, or mutation forwarding.
function previewApiProxy(next, port = 8000) {
  return (request, response, done) => {
    if (!request.url?.startsWith('/v1/')) return next(request, response, done);
    const fail = (status, code, message, retryable) => {
      if (response.writableEnded || response.destroyed) return;
      response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      response.end(JSON.stringify({ error: { code, message, retryable, request_id: randomUUID() } }));
    };
    if (request.method !== 'GET') return fail(405, 'METHOD_NOT_ALLOWED', 'This development transport supports reads only.', false);
    let path;
    try { path = new URL(request.url, 'http://localhost').pathname; } catch { return fail(422, 'INVALID_PATH', 'Invalid preview path.', false); }
    if (path !== '/v1/me' && path !== '/v1/entertainment/feed' && !/^\/v1\/entertainment\/videos\/[^/]+\/playback$/.test(path)) return fail(404, 'NOT_FOUND', 'Unknown preview route.', false);
    const headers = { accept: 'application/json' };
    if (typeof request.headers.authorization === 'string') headers.authorization = request.headers.authorization;
    const upstream = http.request({ hostname: '127.0.0.1', port, path: request.url, method: 'GET', headers }, result => {
      if ((result.statusCode ?? 500) >= 300 && (result.statusCode ?? 500) < 400) {
        result.resume(); fail(503, 'PREVIEW_UNAVAILABLE', 'Preview redirects are not supported.', true); return;
      }
      let size = 0; const chunks = [];
      result.on('data', chunk => {
        size += chunk.length;
        if (size > 4 * 1024 * 1024) { fail(503, 'PREVIEW_UNAVAILABLE', 'Preview response exceeded its limit.', true); upstream.destroy(); }
        else chunks.push(chunk);
      });
      result.on('end', () => {
        if (response.writableEnded || response.destroyed) return;
        response.writeHead(result.statusCode ?? 502, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        response.end(Buffer.concat(chunks));
      });
      result.on('error', () => fail(503, 'PREVIEW_UNAVAILABLE', 'Preview response was interrupted. Retry.', true));
    });
    const timer = setTimeout(() => { fail(503, 'PREVIEW_UNAVAILABLE', 'Preview timed out. Retry.', true); upstream.destroy(); }, 12000);
    upstream.on('error', () => fail(503, 'PREVIEW_UNAVAILABLE', 'The preview API is unavailable. Retry shortly.', true));
    response.on('close', () => { clearTimeout(timer); upstream.destroy(); });
    upstream.end();
  };
}
module.exports = { previewApiProxy };
