export interface StartupSnapshot {
  schema_version: 1; started_at: string; phase: 'bootstrap' | 'page' | 'source' | 'frame';
  page_ms: number | null; source_ms: number | null; first_frame_ms: number | null;
  cache_hit: boolean; starter_alias: boolean;
}
/** Local bounded timing evidence only: no account, occurrence, URL or asset IDs. */
export class StartupTrace {
  private started = 0;
  private snapshot: StartupSnapshot | null = null;
  private writes: Promise<unknown> = Promise.resolve();
  constructor(private write: (value: StartupSnapshot) => Promise<void>, private now = Date.now) {}
  private save() { const value = { ...this.snapshot! }; this.writes = this.writes.catch(() => undefined).then(() => this.write(value)).catch(() => undefined); }
  start() {
    this.started = this.now();
    this.snapshot = { schema_version: 1, started_at: new Date(this.started).toISOString(), phase: 'bootstrap', page_ms: null, source_ms: null, first_frame_ms: null, cache_hit: false, starter_alias: false }; this.save();
  }
  cancel() { this.snapshot = null; }
  page() { if (!this.snapshot) return; this.snapshot.page_ms = this.now() - this.started; this.snapshot.phase = 'page'; this.save(); }
  source(cacheHit: boolean, starterAlias: boolean) {
    if (!this.snapshot || this.snapshot.source_ms !== null) return;
    this.snapshot.source_ms = this.now() - this.started; this.snapshot.cache_hit = cacheHit; this.snapshot.starter_alias = starterAlias; this.snapshot.phase = 'source'; this.save();
  }
  frame() {
    if (!this.snapshot || this.snapshot.source_ms === null || this.snapshot.first_frame_ms !== null) return;
    this.snapshot.first_frame_ms = this.now() - this.started; this.snapshot.phase = 'frame'; this.save();
  }
}
