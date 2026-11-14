export interface WarmAsset { url: string; kind: string; expires_at: string | null }
export interface WarmDriver { warm(url: string, signal: AbortSignal): Promise<void>; stop(): void }

/** One serial, silent worker, separate from the active and immediate-next players.
 * It warms starts, not entire movies. Stale lookahead is cancelled, never queued. */
export class MediaWarmup {
  private desired: string[] = [];
  private done = new Set<string>();
  private running: { url: string; abort: AbortController } | null = null;
  private enabled = false;
  private disposed = false;
  constructor(private driver: WarmDriver, private now = Date.now) {}
  update(assets: WarmAsset[], enabled: boolean) {
    if (this.disposed) return;
    this.enabled = enabled;
    this.desired = [...new Set(assets.filter(asset => asset.kind === 'mp4' && (!asset.expires_at || Date.parse(asset.expires_at) > this.now() + 30000)).map(asset => asset.url).filter(url => {
      try { const u = new URL(url); return u.protocol === 'https:' && !u.username && !u.password; } catch { return false; }
    }))].slice(0, 6);
    // Retain only this window's completed URLs; owner-scoped lifetime is the hook.
    this.done = new Set([...this.done].filter(url => this.desired.includes(url)));
    if (this.running && (!enabled || !this.desired.includes(this.running.url))) this.running.abort.abort();
    if (!enabled) this.driver.stop();
    this.pump();
  }
  private pump() {
    if (this.disposed || !this.enabled || this.running) return;
    const url = this.desired.find(uri => !this.done.has(uri)); if (!url) return;
    const task = { url, abort: new AbortController() }; this.running = task;
    void this.driver.warm(url, task.abort.signal).catch(() => undefined).finally(() => {
      if (!task.abort.signal.aborted) this.done.add(url); // Failed assets retry on a later window, never spin.
      this.running = null; this.pump();
    });
  }
  dispose() { this.disposed = true; this.running?.abort.abort(); this.desired = []; this.done.clear(); this.driver.stop(); }
}

export function hasBufferHeadroom(buffered: number, position: number, duration: number) {
  if (!Number.isFinite(buffered) || buffered < 0 || !Number.isFinite(position)) return false;
  return buffered - position >= 2 || (duration > 0 && duration - position < 2 && buffered >= duration - 0.1);
}
