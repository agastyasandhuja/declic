const http = require('node:http');
const { randomUUID } = require('node:crypto');

// Opt-in local demo transport. Fixed loopback destination, route/method allowlist,
// bearer auth only; neither cookies nor redirects cross this boundary.
const routes = [
  ['GET', /^\/v1\/learning\/(settings|demo-catalog)$/],
  ['PATCH', /^\/v1\/learning\/settings$/],
  ['GET', /^\/v1\/entertainment\/videos\/[^/]+\/comments$/],
  ['GET', /^\/v1\/(me|feed|learning\/progress|preparation|canvas\/connection|instagram\/connection|academics\/profile|entertainment\/feed)$/],
  ['GET', /^\/v1\/(academics\/jobs\/[^/]+|(learning|entertainment)\/videos\/[^/]+(\/playback)?)$/],
  ['POST', /^\/v1\/(feed\/(sessions|events)|canvas\/(token|sync)|instagram\/(connect|browser-session)|preparation\/retry)$/],
  ['POST', /^\/v1\/(feed\/sessions\/[^/]+\/quiz-gate|quizzes\/[^/]+\/(answers|recover))$/],
  ['DELETE', /^\/v1\/(canvas|instagram)\/connection$/],
];
function previewApiProxy(next, port = 8000) {
  return (request, response, done) => {
    if (!request.url?.startsWith('/v1/')) return next(request, response, done);
    const fail = (status, code, message, retryable = false) => {
      if (response.writableEnded || response.destroyed) return;
      response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      response.end(JSON.stringify({ error: { code, message, retryable, request_id: randomUUID() } }));
    };
    let path;
    try { path = new URL(request.url, 'http://localhost').pathname; } catch { return fail(422, 'INVALID_PATH', 'Invalid preview path.'); }
    if (/%2f|%5c|\\/i.test(path)) return fail(404, 'NOT_FOUND', 'Unknown preview route.');
    const matching = routes.filter(([, route]) => route.test(path));
    if (!matching.length) return fail(404, 'NOT_FOUND', 'Unknown preview route.');
    if (!matching.some(([method]) => method === request.method)) return fail(405, 'METHOD_NOT_ALLOWED', 'Unsupported method.');
    if (!/^Bearer \S+$/i.test(request.headers.authorization ?? '')) return fail(401, 'AUTH_REQUIRED', 'Sign in to continue.');
    const headers = { accept: 'application/json', authorization: request.headers.authorization };
    if (request.headers['idempotency-key']) headers['idempotency-key'] = request.headers['idempotency-key'];
    const chunks = []; let size = 0;
    request.on('data', chunk => { size += chunk.length; if (size > 64 * 1024) { fail(413, 'BODY_TOO_LARGE', 'Request exceeded its limit.'); } else chunks.push(chunk); });
    request.on('end', () => {
      if (response.writableEnded || response.destroyed) return;
      if (chunks.length) headers['content-type'] = 'application/json';
      const upstream = http.request({ hostname: '127.0.0.1', port, path: request.url, method: request.method, headers }, result => {
        if ((result.statusCode ?? 500) >= 300 && (result.statusCode ?? 500) < 400) { result.resume(); fail(503, 'PREVIEW_UNAVAILABLE', 'Preview redirects are not supported.', true); return; }
        let bytes = 0; const output = [];
        result.on('data', chunk => { bytes += chunk.length; if (bytes > 4 * 1024 * 1024) { fail(503, 'PREVIEW_UNAVAILABLE', 'Response exceeded its limit.', true); upstream.destroy(); } else output.push(chunk); });
        result.on('end', () => {
          if (response.writableEnded || response.destroyed) return;
          const outgoing = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
          const retryAfter = result.headers['retry-after'];
          if (typeof retryAfter === 'string' && /^\d{1,3}$/.test(retryAfter)) outgoing['Retry-After'] = String(Math.min(300, Number(retryAfter)));
          response.writeHead(result.statusCode ?? 502, outgoing); response.end(Buffer.concat(output));
        });
        result.on('error', () => fail(503, 'PREVIEW_UNAVAILABLE', 'Response interrupted. Retry.', true));
      });
      const timer = setTimeout(() => { fail(503, 'PREVIEW_UNAVAILABLE', 'Preview timed out. Retry.', true); upstream.destroy(); }, 65000);
      upstream.on('error', () => fail(503, 'PREVIEW_UNAVAILABLE', 'The API is unavailable. Retry shortly.', true));
      response.on('close', () => { clearTimeout(timer); upstream.destroy(); });
      upstream.end(Buffer.concat(chunks));
    });
  };
}
module.exports = { previewApiProxy };
