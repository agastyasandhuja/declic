import { ApiError, type ApiClient } from '../../lib/api/client';
import { parseUnifiedPage, type UnifiedPage } from './unified';

interface Dependencies {
  preferred(scope: string): Promise<string[]>;
  authorize(scope: string, page: UnifiedPage): Promise<void>;
  requestId(): string;
  started?(): void; received?(page: UnifiedPage): void; cancelled?(): void;
}
/** One eager fresh server response, shared with the first mounted feed. Nothing
 * is replayed from disk: occurrence IDs, quiz gates and order remain server-owned. */
export class FeedBootstrap {
  private entry: { scope: string; api: ApiClient; promise: Promise<UnifiedPage>; abort: AbortController; claimed: boolean } | null = null;
  private generation = 0;
  constructor(private deps: Dependencies) {}
  cancel() { this.deps.cancelled?.(); this.generation++; this.entry?.abort.abort(); this.entry = null; }
  begin(scope: string, api: ApiClient) {
    if (this.entry?.scope === scope && this.entry.api === api && !this.entry.claimed) return;
    this.cancel(); this.deps.started?.(); const generation = this.generation, abort = new AbortController();
    const promise = (async () => {
      const ids = await this.deps.preferred(scope).catch(() => []);
      if (generation !== this.generation) throw new Error('Feed startup changed.');
      let page: UnifiedPage;
      for (let attempt = 0; ; attempt++) {
        try {
          page = parseUnifiedPage(await api.request('/v1/feed/bootstrap', {
            method: 'POST', body: { limit: 5, preferred_video_ids: ids.slice(0, 6) },
            signal: abort.signal, headers: { 'Idempotency-Key': this.deps.requestId() },
          })); break;
        } catch (error) {
          if (generation !== this.generation || attempt > 0 || !(error instanceof ApiError) || error.code !== 'STALE_BOOTSTRAP') throw error;
        }
      }
      if (generation !== this.generation) throw new Error('Feed startup changed.');
      await this.deps.authorize(scope, page).catch(() => undefined);
      if (generation !== this.generation) throw new Error('Feed startup changed.');
      this.deps.received?.(page);
      return page;
    })();
    this.entry = { scope, api, promise, abort, claimed: false };
    void promise.catch(() => undefined); // The mounted screen owns visible errors/retry.
  }
  take(scope: string, api: ApiClient) {
    if (!this.entry || this.entry.scope !== scope || this.entry.api !== api || this.entry.claimed) this.begin(scope, api);
    const entry = this.entry!; entry.claimed = true;
    return entry.promise;
  }
}
