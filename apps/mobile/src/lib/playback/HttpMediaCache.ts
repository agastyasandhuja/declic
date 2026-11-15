export interface MediaFileEntry { key: string; bytes: number; expires: number; used: number }
export interface MediaFileStore {
  key(url: string): Promise<string>; load(): Promise<MediaFileEntry[]>; save(entries: MediaFileEntry[]): Promise<void>;
  exists(key: string): Promise<boolean>; uri(key: string): string;
  download(url: string, key: string, signal: AbortSignal, maxBytes: number): Promise<number>;
  remove(key: string): Promise<void>; clear(): Promise<void>;
}
/** Completed files only. One bounded HTTP download, no player or audio session.
 * Remote URLs never persist; freshly authenticated URLs remain the lookup key. */
export class HttpMediaCache {
  private entries = new Map<string, MediaFileEntry>();
  private pinned = new Map<string, number>();
  private epoch = 0;
  private ready = false;
  private task: AbortController | null = null;
  private queue: Promise<unknown> = Promise.resolve();
  constructor(private store: MediaFileStore, private now = Date.now, private budget = 128 * 1024 * 1024, private maxFile = 20 * 1024 * 1024) {}
  get generation() { return this.epoch; }
  deactivate() { this.epoch++; this.ready = false; this.entries.clear(); this.pinned.clear(); this.task?.abort(); }
  async clear() {
    this.deactivate();
    const run = this.queue.catch(() => undefined).then(() => this.store.clear());
    this.queue = run; await run;
  }
  async open() {
    const epoch = this.epoch;
    const run = this.queue.catch(() => undefined).then(async () => {
    if (epoch !== this.epoch) return;
    const stored = await this.store.load();
    if (epoch !== this.epoch) return;
    this.entries.clear();
    for (const entry of stored) {
      if (!/^[a-f0-9]{64}$/.test(entry.key) || !Number.isFinite(entry.bytes) || entry.bytes <= 0 || entry.bytes > this.maxFile || !Number.isFinite(entry.expires) || !Number.isFinite(entry.used)) continue;
      if (entry.expires > this.now()) this.entries.set(entry.key, entry);
      else await this.store.remove(entry.key);
    }
    await this.trim(0);
    if (epoch === this.epoch) this.ready = true;
    });
    this.queue = run; await run;
  }
  async resolve(url: string) {
    if (!this.ready) return url;
    const epoch = this.epoch, key = await this.store.key(url), entry = this.entries.get(key);
    if (!entry || entry.expires <= this.now() || !await this.store.exists(key) || this.entries.get(key) !== entry || epoch !== this.epoch || !this.ready) return url;
    entry.used = this.now(); this.pinned.set(key, (this.pinned.get(key) ?? 0) + 1);
    return this.store.uri(key);
  }
  async release(url: string, epoch = this.epoch) {
    const key = await this.store.key(url);
    if (epoch !== this.epoch) return;
    const count = this.pinned.get(key) ?? 0;
    if (count > 1) this.pinned.set(key, count - 1); else this.pinned.delete(key);
  }
  async discard(url: string) {
    const epoch = this.epoch;
    const run = this.queue.catch(() => undefined).then(async () => {
      const key = await this.store.key(url);
      if (epoch !== this.epoch) return;
      this.entries.delete(key); this.pinned.delete(key);
      await this.store.remove(key); await this.store.save([...this.entries.values()]);
    });
    this.queue = run; await run;
  }
  private async trim(incoming: number) {
    let bytes = [...this.entries.values()].reduce((sum, entry) => sum + entry.bytes, 0);
    for (const entry of [...this.entries.values()].sort((a, b) => a.used - b.used)) {
      if (entry.expires > this.now() && bytes + incoming <= this.budget) continue;
      if (this.pinned.has(entry.key)) continue;
      this.entries.delete(entry.key); bytes -= entry.bytes; await this.store.remove(entry.key);
    }
    if (bytes + incoming > this.budget) throw new Error('Media cache budget unavailable');
  }
  warm(url: string, expiresAt: string | null, signal: AbortSignal): Promise<void> {
    const epoch = this.epoch;
    const run = this.queue.catch(() => undefined).then(async () => {
      if (!this.ready || signal.aborted || epoch !== this.epoch) return;
      const source = new URL(url);
      if (source.protocol !== 'https:' || source.username || source.password) return;
      const expires = Math.min(this.now() + 15 * 60 * 1000, expiresAt ? Date.parse(expiresAt) : Infinity);
      if (!Number.isFinite(expires) || expires <= this.now() + 30000) return;
      const key = await this.store.key(url);
      if (signal.aborted || epoch !== this.epoch || !this.ready) return;
      const prior = this.entries.get(key);
      if (prior && prior.expires > this.now() && await this.store.exists(key)) return;
      await this.trim(this.maxFile);
      if (signal.aborted || epoch !== this.epoch || !this.ready) return;
      const abort = new AbortController(); this.task = abort;
      const cancel = () => abort.abort(); signal.addEventListener('abort', cancel, { once: true });
      try {
        const bytes = await this.store.download(url, key, abort.signal, this.maxFile);
        if (abort.signal.aborted || epoch !== this.epoch || !this.ready || expires <= this.now() || bytes <= 0 || bytes > this.maxFile) { await this.store.remove(key); return; }
        this.entries.set(key, { key, bytes, expires, used: this.now() });
        await this.store.save([...this.entries.values()]);
      } finally { signal.removeEventListener('abort', cancel); if (this.task === abort) this.task = null; }
    });
    this.queue = run; return run;
  }
}
