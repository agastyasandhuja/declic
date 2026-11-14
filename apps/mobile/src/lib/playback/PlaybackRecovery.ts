/** Treat a URL near expiry as stale before granting playback after app resume. */
export function needsPlaybackRefresh(expiresAt: string | null | undefined, now = Date.now()) {
  if (!expiresAt) return false;
  const expiry = Date.parse(expiresAt);
  return !Number.isFinite(expiry) || expiry <= now + 10000;
}

/** One automatic owned-URL resolution per selected foreground visit, never a loop. */
export class PlaybackRecovery {
  private itemId: string | null = null;
  private active = false;
  private attempted = false;
  observe(itemId: string | null, active: boolean) {
    if (itemId !== this.itemId || (active && !this.active)) this.attempted = false;
    this.itemId = itemId;
    this.active = active;
  }
  claim(itemId: string) {
    if (!this.active || this.itemId !== itemId || this.attempted) return false;
    this.attempted = true;
    return true;
  }
}

/** Retain the last observed media position while a renewed source seeks back. */
export class PlaybackSeek {
  private pending: { itemId: string; positionMs: number; afterSelection: number; requestedAt: number | null } | null = null;
  clear() { this.pending = null; }
  capture(itemId: string, positionMs: number, afterSelection: number) {
    const previous = this.pending?.itemId === itemId ? this.pending.positionMs : 0;
    this.pending = { itemId, positionMs: Math.max(previous, Number.isFinite(positionMs) ? positionMs : 0), afterSelection, requestedAt: null };
  }
  anchor(itemId: string, actualMs: number) {
    return this.pending?.itemId === itemId ? this.pending.positionMs : actualMs;
  }
  isPending(itemId: string) { return this.pending?.itemId === itemId; }
  takeTarget(itemId: string, selection: number, now: number) {
    if (!this.pending || this.pending.itemId !== itemId || selection <= this.pending.afterSelection || this.pending.requestedAt !== null) return null;
    this.pending.requestedAt = now;
    return this.pending.positionMs;
  }
  settled(itemId: string, actualMs: number, durationMs: number, now: number): 'ready' | 'waiting' | 'timeout' {
    const value = this.pending;
    if (!value || value.itemId !== itemId) return 'ready';
    if (value.requestedAt === null) return 'waiting';
    // The same duration-end wrap accepted by the server is a legitimate resumed loop.
    const looped = durationMs > 0 && value.positionMs >= durationMs - 4000 && actualMs <= 4000;
    if (actualMs >= value.positionMs || looped) { this.pending = null; return 'ready'; }
    return now - value.requestedAt >= 5000 ? 'timeout' : 'waiting';
  }
}
