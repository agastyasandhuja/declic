export class ApiError extends Error {
  constructor(message: string, public status: number, public code: string, public retryable: boolean, public requestId?: string, public retryAfterMs?: number) { super(message); }
}

export interface RequestOptions extends Omit<RequestInit, 'body'> { body?: unknown }
export interface ApiClient { request<T>(path: string, options?: RequestOptions): Promise<T> }
export interface ApiClientOptions {
  baseUrl: string;
  getAccessToken(forceRefresh?: boolean): Promise<string | null>;
  onUnauthorized(): void;
  fetcher?: typeof fetch;
  timeoutMs?: number;
}

export function createApiClient({ baseUrl, getAccessToken, onUnauthorized, fetcher = fetch, timeoutMs = 15000 }: ApiClientOptions): ApiClient {
  let refresh: Promise<string | null> | null = null;
  const readToken = async (force = false) => {
    try { return await getAccessToken(force); }
    catch { throw new ApiError('Unable to verify your session. Check your connection and retry.', 0, 'AUTH_UNAVAILABLE', true); }
  };
  return { async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    if (!baseUrl) throw new ApiError('Add an API URL in local configuration to connect your backend.', 0, 'API_NOT_CONFIGURED', false);
    let origin: URL;
    try { origin = new URL(baseUrl); } catch { throw new ApiError('Configure a valid HTTPS API origin.', 0, 'INVALID_API_ORIGIN', false); }
    if (origin.protocol !== 'https:' || origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) throw new ApiError('The authenticated API requires an HTTPS origin.', 0, 'INVALID_API_ORIGIN', false);
    const url = new URL(path, origin);
    if (!path.startsWith('/v1/') || !url.pathname.startsWith('/v1/') || /%2f|%5c|\\/i.test(url.pathname) || url.origin !== origin.origin || url.hash) throw new ApiError('API requests must use a /v1/ path on the configured server.', 0, 'INVALID_API_PATH', false);
    let token = await readToken();
    if (!token) throw new ApiError('Sign in to use connected features. Demo mode has no API credentials.', 401, 'AUTH_REQUIRED', false);
    const headers = new Headers(options.headers);
    headers.set('Accept', 'application/json');
    if (options.body !== undefined) headers.set('Content-Type', 'application/json');
    const method = (options.method ?? 'GET').toUpperCase();
    const canReplay = ['GET', 'HEAD', 'OPTIONS'].includes(method) || headers.has('Idempotency-Key');
    for (let attempt = 0; attempt < 2; attempt++) {
      const controller = new AbortController();
      const abort = () => controller.abort();
      options.signal?.addEventListener('abort', abort, { once: true });
      if (options.signal?.aborted) controller.abort();
      const timer = setTimeout(abort, timeoutMs);
      let response: Response;
      let payload: any;
      try {
        headers.set('Authorization', `Bearer ${token}`);
        // The deadline includes the response body: headers alone are not completion.
        const operation = async () => {
          const result = await fetcher(url.toString(), { ...options, method, headers, body: options.body === undefined ? undefined : JSON.stringify(options.body), signal: controller.signal, redirect: 'error' });
          const body = result.status === 204 ? null : await result.json().catch(() => null);
          return { result, body };
        };
        const aborted = new Promise<never>((_resolve, reject) => {
          if (controller.signal.aborted) reject(new Error('aborted'));
          else controller.signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
        });
        const completed = await Promise.race([operation(), aborted]);
        response = completed.result; payload = completed.body;
      } catch {
        throw new ApiError(controller.signal.aborted ? 'Request cancelled or timed out. Try again.' : 'Unable to reach the server. Check your connection and retry.', 0, 'NETWORK_ERROR', true);
      } finally {
        clearTimeout(timer);
        options.signal?.removeEventListener('abort', abort);
      }
      if (response.status === 401 && attempt === 0) {
        refresh ??= readToken(true).finally(() => { refresh = null; });
        token = await refresh;
        if (token && canReplay) continue;
        if (token) throw new ApiError('Session refreshed. Retry this action with an Idempotency-Key.', 409, 'RETRY_WITH_IDEMPOTENCY', true);
      }
      if (response.status === 401) onUnauthorized();
      if (response.status === 204) return undefined as T;
      if (!response.ok) {
        const detail = payload?.error;
        const retryAfter = response.headers?.get('Retry-After');
        const retryAfterMs = retryAfter && /^\d{1,3}$/.test(retryAfter) ? Math.min(300000, Number(retryAfter) * 1000) : undefined;
        throw new ApiError(typeof detail?.message === 'string' ? detail.message : `Request failed (${response.status}).`, response.status, typeof detail?.code === 'string' ? detail.code : 'REQUEST_FAILED', typeof detail?.retryable === 'boolean' ? detail.retryable : response.status >= 500, typeof detail?.request_id === 'string' ? detail.request_id : undefined, retryAfterMs);
      }
      if (payload === null) throw new ApiError('The server returned an unreadable response.', response.status, 'INVALID_RESPONSE', true);
      return payload as T;
    }
    throw new ApiError('Your session has expired. Please sign in again.', 401, 'AUTH_EXPIRED', false);
  } };
}
