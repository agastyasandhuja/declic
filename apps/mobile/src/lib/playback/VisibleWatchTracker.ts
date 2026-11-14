/** Count media movement while continuously visible; stalls, seeks and gaps earn no time. */
export class VisibleWatchTracker {
  totalMs = 0;
  private previous: { positionMs: number; nowMs: number; eligible: boolean } | null = null;
  sample(positionMs: number, nowMs: number, eligible: boolean, durationMs?: number) {
    const previous = this.previous;
    this.previous = { positionMs, nowMs, eligible };
    if (!previous || !eligible || !previous.eligible || !Number.isFinite(positionMs)) return this.totalMs;
    const wall = nowMs - previous.nowMs;
    if (wall <= 0 || wall > 1500) return this.totalMs;
    let movement = positionMs - previous.positionMs;
    if (movement < 0 && durationMs && previous.positionMs >= durationMs - 1500 && positionMs < 1500) movement = durationMs - previous.positionMs + positionMs;
    if (movement > 0 && movement <= wall * 1.5 + 100) this.totalMs += Math.min(wall, movement);
    return this.totalMs;
  }
}

/** A loaded stream can stall later too; paused/background time never times it out. */
export class PlaybackStallGuard {
  private lastPosition = NaN;
  private lastMovement: number | null = null;
  constructor(private timeoutMs = 15000) {}
  sample(positionMs: number, nowMs: number, enabled: boolean) {
    if (!enabled || this.lastMovement === null || !Number.isFinite(this.lastPosition) || Math.abs(positionMs - this.lastPosition) > 20) this.lastMovement = nowMs;
    this.lastPosition = positionMs;
    return enabled && nowMs - this.lastMovement >= this.timeoutMs;
  }
}

/** Audio/media time can advance without a picture; require an actual video frame. */
export class FirstFrameGuard {
  private selection: number | null = null;
  private started: number | null = null;
  constructor(private timeoutMs = 12000) {}
  sample(selection: number, rendered: boolean, nowMs: number, enabled: boolean) {
    if (this.selection !== selection || !enabled || rendered) this.started = null;
    this.selection = selection;
    if (!enabled || rendered) return false;
    this.started ??= nowMs;
    return nowMs - this.started >= this.timeoutMs;
  }
}
