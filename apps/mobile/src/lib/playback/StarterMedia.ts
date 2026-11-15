import type { HttpMediaCache } from './HttpMediaCache';
import type { UnifiedItem } from '../../features/feed/unified';
type Hint = { video_id: string; asset_id: string; key: string; expires: number };
interface Storage { read(): Promise<string | null>; write(value: string | null): Promise<void> }
/** A hint is never authorization: only a fresh server-issued entertainment card
 * can associate a renewed URL with a completed, unexpired file for this owner. */
export class StarterMedia {
  private scope: string | null = null;
  private epoch = 0;
  private hints: Hint[] = [];
  private aliases = new Map<string, Hint>();
  private queue: Promise<unknown> = Promise.resolve();
  constructor(private cache: HttpMediaCache, private storage: Storage, private now = Date.now) {}
  deactivate() { this.epoch++; this.scope = null; this.hints = []; this.aliases.clear(); }
  async open(scope: string | null) {
    this.deactivate(); this.scope = scope; const epoch = this.epoch;
    const task = this.queue.catch(() => undefined).then(async () => {
      if (!scope) { await this.storage.write(null); return; }
      const raw = await this.storage.read();
      if (epoch !== this.epoch) return;
      try {
        const data = JSON.parse(raw ?? 'null');
        if (data?.scope !== scope || !Array.isArray(data.hints)) return;
        this.hints = data.hints.filter((h: Hint) => h && typeof h.video_id === 'string' && h.video_id.length > 0 && h.video_id.length <= 200 && typeof h.asset_id === 'string' && h.asset_id.length > 0 && h.asset_id.length <= 200 && /^[a-f0-9]{64}$/.test(h.key) && Number.isFinite(h.expires) && h.expires > this.now()).slice(0, 12);
      } catch { /* Corrupt hints are optional; fresh feed still works. */ }
    });
    this.queue = task; await task;
  }
  async record(videoId: string, assetId: string, url: string) {
    const epoch = this.epoch, scope = this.scope;
    if (!scope || !videoId || videoId.length > 200 || !assetId || assetId.length > 200) return;
    const file = await this.cache.describe(url);
    if (!file || file.expires <= this.now() + 30000 || epoch !== this.epoch) return;
    this.hints = [{ video_id: videoId, asset_id: assetId, key: file.key, expires: file.expires }, ...this.hints.filter(h => h.video_id !== videoId && h.expires > this.now())].slice(0, 12);
    const data = JSON.stringify({ scope, hints: this.hints });
    const task = this.queue.catch(() => undefined).then(async () => { if (epoch === this.epoch) await this.storage.write(data); });
    this.queue = task; await task;
  }
  async preferred(scope: string) {
    const epoch = this.epoch;
    if (scope !== this.scope) return [];
    const available = await Promise.all(this.hints.map(async h => h.expires > this.now() + 30000 && await this.cache.describeKey(h.key) ? h.video_id : null));
    return epoch === this.epoch ? [...new Set(available.filter((id): id is string => !!id))].slice(0, 6) : [];
  }
  async authorize(scope: string, items: UnifiedItem[]) {
    const epoch = this.epoch;
    if (scope !== this.scope) return;
    for (const item of items) {
      if (item.kind !== 'entertainment_video') continue;
      const hint = this.hints.find(h => h.video_id === item.video.video_id && h.asset_id === item.video.playback.asset_id);
      const expiry = item.video.playback.expires_at ? Date.parse(item.video.playback.expires_at) : Infinity;
      if (!hint || hint.expires <= this.now() || expiry <= this.now() || !await this.cache.describeKey(hint.key)) continue;
      if (epoch !== this.epoch) return;
      this.aliases.set(item.video.playback.url, { ...hint, expires: Math.min(hint.expires, expiry) });
    }
    while (this.aliases.size > 80) this.aliases.delete(this.aliases.keys().next().value!);
  }
  keyFor(url: string) { const hint = this.aliases.get(url); return hint && hint.expires > this.now() ? hint.key : undefined; }
  forget(url: string) { this.aliases.delete(url); }
}
