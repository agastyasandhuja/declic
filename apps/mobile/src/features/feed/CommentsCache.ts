import type { ApiClient } from '../../lib/api/client';
import { parseCommentsPage, type CommentsPage } from './commentsData';
interface Flight { promise: Promise<CommentsPage>; abort: AbortController; subscribers: number }

export class CommentsCache {
  private pages = new Map<string, { at: number; page: CommentsPage }>();
  private flights = new Map<string, Flight>();
  constructor(private api: ApiClient, private now = Date.now) {}
  peek(videoId: string): CommentsPage | null {
    const entry = this.pages.get(videoId);
    if (!entry || this.now() - entry.at > 60000) { this.pages.delete(videoId); return null; }
    this.pages.delete(videoId); this.pages.set(videoId, entry); return entry.page;
  }
  async read(videoId: string, cursor: string | null, signal: AbortSignal): Promise<CommentsPage> {
    if (signal.aborted) throw new Error('Cancelled');
    const cached = !cursor && this.peek(videoId); if (cached) return cached;
    const key = JSON.stringify([videoId, cursor]);
    let flight = this.flights.get(key);
    if (!flight) {
      const controller = new AbortController();
      const query = new URLSearchParams({ limit: '20' }); if (cursor) query.set('cursor', cursor);
      const pending: Flight = { abort: controller, subscribers: 0, promise: Promise.resolve(null as never) };
      pending.promise = this.api.request(`/v1/entertainment/videos/${encodeURIComponent(videoId)}/comments?${query}`, { signal: controller.signal }).then(value => {
        const page = parseCommentsPage(value);
        if (!cursor && !controller.signal.aborted) {
          this.pages.set(videoId, { at: this.now(), page });
          while (this.pages.size > 12) this.pages.delete(this.pages.keys().next().value!);
        }
        return page;
      }).finally(() => { if (this.flights.get(key) === pending) this.flights.delete(key); });
      flight = pending; this.flights.set(key, flight);
    }
    const shared = flight; shared.subscribers++;
    return new Promise((resolve, reject) => {
      let settled = false;
      const finish = (error: unknown, page?: CommentsPage) => {
        if (settled) return; settled = true; signal.removeEventListener('abort', cancel); shared.subscribers--;
        // An opening sheet can adopt its warmup in the same React commit.
        queueMicrotask(() => { if (shared.subscribers === 0 && this.flights.get(key) === shared) { shared.abort.abort(); this.flights.delete(key); } });
        if (error) reject(error); else resolve(page!);
      };
      const cancel = () => finish(new Error('Cancelled'));
      signal.addEventListener('abort', cancel, { once: true });
      shared.promise.then(page => finish(null, page), error => finish(error));
      if (signal.aborted) cancel();
    });
  }
}
const owners = new WeakMap<ApiClient, Map<string, CommentsCache>>();
export function commentsFor(api: ApiClient, owner: string): CommentsCache {
  let byOwner = owners.get(api); if (!byOwner) { byOwner = new Map(); owners.set(api, byOwner); }
  let cache = byOwner.get(owner); if (!cache) { cache = new CommentsCache(api); byOwner.set(owner, cache); }
  // Account IDs are explicit; ApiClient may survive a direct user switch.
  for (const key of byOwner.keys()) if (key !== owner) byOwner.delete(key);
  return cache;
}
