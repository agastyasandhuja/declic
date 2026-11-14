export type HoldZone = 'edge' | 'center';
export interface InteractionState { speed: 1 | 2; hidden: boolean; menu: boolean; scrubbing: boolean; comments: boolean }
const idle = (): InteractionState => ({ speed: 1, hidden: false, menu: false, scrubbing: false, comments: false });

/** Transient gestures belong to one visible clip, never persist across navigation. */
export class FeedInteraction {
  state = idle();
  private active = false;
  private selection: string | null = null;
  constructor(private publish: (state: InteractionState) => void, private setRate: (rate: 1 | 2) => void, private confirmHold: () => void = () => {}) {}
  private update(patch: Partial<InteractionState>) {
    this.state = { ...this.state, ...patch };
    this.setRate(this.state.speed); this.publish(this.state);
  }
  observe(selection: string | null, active: boolean) {
    if (this.selection !== selection || !active) this.reset();
    this.selection = selection; this.active = active;
  }
  hold(zone: HoldZone) {
    if (!this.active || !this.selection || this.state.scrubbing || this.state.comments || this.state.menu) return;
    if (zone === 'edge' && this.state.speed !== 2) this.confirmHold();
    this.update(zone === 'edge' ? { speed: 2, hidden: true } : { speed: 1, hidden: false, menu: true });
  }
  release() { if (this.state.speed !== 1 || this.state.hidden) this.update({ speed: 1, hidden: false }); }
  openComments() { if (this.active && this.selection) this.update({ speed: 1, hidden: false, menu: false, comments: true }); }
  closeOverlay() { this.update({ menu: false, comments: false, speed: 1, hidden: false }); }
  scrub(active: boolean) {
    if (active && (!this.active || !this.selection || this.state.menu || this.state.comments)) return;
    this.update({ scrubbing: active, speed: 1, hidden: false });
  }
  reset() { this.state = idle(); this.setRate(1); this.publish(this.state); }
  dispose() { this.active = false; this.selection = null; this.reset(); }
}

export function scrubTarget(locationX: number, width: number, duration: number) {
  if (!Number.isFinite(locationX) || !Number.isFinite(width) || !Number.isFinite(duration) || width <= 0 || duration <= 0) return null;
  return Math.min(Math.max(0, duration - 0.05), Math.max(0, locationX / width * duration));
}

export function interactionGates(state: InteractionState) {
  return { playbackBlocked: state.menu || state.scrubbing, scrollBlocked: state.menu || state.scrubbing || state.comments };
}
