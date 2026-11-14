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
