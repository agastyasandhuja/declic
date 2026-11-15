export const DOUBLE_TAP_MS = 280;
export const DOUBLE_TAP_SLOP = 40;

type Schedule = (run: () => void, ms: number) => unknown;
type Cancel = (handle: unknown) => void;

/**
 * Splits taps on a clip into a delayed single tap (pause/play) and an immediate
 * double tap ("click"). A double tap never also toggles playback.
 */
export class TapGesture {
  private last: { t: number; x: number; y: number } | null = null;
  private pending: unknown = null;
  constructor(
    private onSingle: () => void,
    private onDouble: (x: number, y: number) => void,
    private schedule: Schedule = (run, ms) => setTimeout(run, ms),
    private cancel: Cancel = handle => clearTimeout(handle as ReturnType<typeof setTimeout>),
  ) {}
  tap(x: number, y: number, now: number) {
    const last = this.last;
    if (last && now - last.t < DOUBLE_TAP_MS && Math.abs(x - last.x) < DOUBLE_TAP_SLOP && Math.abs(y - last.y) < DOUBLE_TAP_SLOP) {
      this.clear(); this.last = null;
      this.onDouble(x, y);
      return 'double' as const;
    }
    this.clear(); this.last = { t: now, x, y };
    this.pending = this.schedule(() => { this.pending = null; this.onSingle(); }, DOUBLE_TAP_MS);
    return 'single' as const;
  }
  /** A long press or scroll must not leave a stale single tap or a half double tap behind. */
  reset() { this.clear(); this.last = null; }
  private clear() { if (this.pending !== null) { this.cancel(this.pending); this.pending = null; } }
}
