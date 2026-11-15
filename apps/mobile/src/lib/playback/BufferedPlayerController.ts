import type { PlaybackGate, PlaybackState, PlayerDriver } from './SinglePlayerController';

export interface BufferedPlaybackState extends PlaybackState { activeSlot: 0 | 1; timedOut: boolean; sourceUri: string | null; selection: number; buffers?: { uri: string | null; ready: boolean; generation: number }[] }
interface Slot { inFlight: boolean; uri: string | null; ready: boolean; version: number; queue: Promise<void>; load: Promise<void> }
const emptySlot = (): Slot => ({ inFlight: false, uri: null, ready: false, version: 0, queue: Promise.resolve(), load: Promise.resolve() });

/** Two bounded media buffers. The standby surface stays mounted but hidden and paused. */
export class BufferedPlayerController {
  private slots: [Slot, Slot] = [emptySlot(), emptySlot()];
  private active: 0 | 1 = 0;
  private version = 0;
  private sourceUri: string | null = null;
  private disposed = false;
  private rate: 1 | 2 = 1;
  private muted = false;
  private commands = [0, 1].map(() => ({ playing: null as boolean | null, muted: null as boolean | null, rate: null as number | null }));
  private failed = false;
  private status = { loading: true, error: null as string | null, timedOut: false };
  private timer: ReturnType<typeof setTimeout> | undefined;
  private gate: PlaybackGate = { foreground: true, focused: true, manuallyPaused: false };
  constructor(private drivers: [PlayerDriver, PlayerDriver], private onState: (state: BufferedPlaybackState) => void, private timeoutMs = 15000) { this.silenceAll(); }
  private emit(loading: boolean, error: string | null = null, timedOut = false) {
    this.status = { loading, error, timedOut };
    if (!this.disposed) this.onState({ buffers: this.slots.map(slot => ({ uri: slot.uri, ready: slot.ready, generation: slot.version })), loading, ready: !loading && !error, error, activeSlot: this.active, timedOut, sourceUri: this.sourceUri, selection: this.version });
  }
  setGate(patch: Partial<PlaybackGate>) { if (this.disposed) return; this.gate = { ...this.gate, ...patch }; this.reconcile(); }
  private mute(slot: number, value: boolean, force = false) {
    if (force || this.commands[slot].muted !== value) { this.commands[slot].muted = value; this.drivers[slot].setMuted?.(value); }
  }
  private playing(slot: number, value: boolean, force = false) {
    if (force || this.commands[slot].playing !== value) { this.commands[slot].playing = value; if (value) this.drivers[slot].play(); else this.drivers[slot].pause(); }
  }
  private silence(slot: number, force = false) { this.mute(slot, true, force); this.playing(slot, false, force); }
  private silenceAll(force = false) { this.silence(0, force); this.silence(1, force); }
  private allowed() { return !this.disposed && !this.failed && this.slots[this.active].ready && this.gate.foreground && this.gate.focused && !this.gate.manuallyPaused; }
  private reconcile() {
    // Commands describe requested playback, not transient native buffering state.
    // Repeated play()/mute writes reconfigure AVAudioSession and disturb playback.
    this.silence(1 - this.active);
    if (this.allowed()) {
      this.mute(this.active, this.muted);
      if (this.commands[this.active].rate !== this.rate) {
        this.commands[this.active].rate = this.rate;
        this.drivers[this.active].setRate?.(this.rate); // May start AVPlayer on iOS.
      }
      this.playing(this.active, true);
    } else this.silence(this.active);
  }
  setMuted(muted: boolean) { if (!this.disposed) { this.muted = muted; this.reconcile(); } }
  /** Native replacement/rate events can arrive after the JS command completes. */
  enforcePlaybackOwner(slot: 0 | 1) {
    if (this.disposed) return;
    if (slot !== this.active || !this.allowed()) this.silence(slot, true);
  }
  private load(slotIndex: 0 | 1, uri: string, force = false) {
    const slot = this.slots[slotIndex];
    if (slot.uri === uri && !force) return slot.load;
    const requested = ++slot.version;
    slot.uri = uri; slot.ready = false; this.silence(slotIndex);
    if (slotIndex !== this.active) this.emit(this.status.loading, this.status.error, this.status.timedOut);
    slot.load = slot.queue = slot.queue.catch(() => undefined).then(async () => {
      if (this.disposed || slot.version !== requested) return;
      slot.inFlight = true;
      try {
        await this.drivers[slotIndex].replaceAsync(uri);
        if (this.disposed || slot.version !== requested) return;
        this.silence(slotIndex, true);
        slot.ready = true;
      } catch {
        if (slot.version === requested) { slot.uri = null; slot.ready = false; }
      } finally { slot.inFlight = false; }
      if (!this.disposed) {
        if (slotIndex !== this.active) this.emit(this.status.loading, this.status.error, this.status.timedOut);
        this.reconcile();
      }
    });
    return slot.load;
  }
  async setSelection(uri: string, upcoming?: string, force = false) {
    if (this.disposed) return;
    const requested = ++this.version;
    this.sourceUri = uri;
    clearTimeout(this.timer);
    this.silenceAll();
    this.failed = false;
    const match = this.slots.findIndex(slot => slot.uri === uri);
    const standby = (1 - this.active) as 0 | 1;
    // A stale, slow preload must not head-of-line block a different selected URI.
    // Reuse the now-paused active slot when it has no replacement in flight.
    this.active = (match >= 0 ? match : this.slots[standby].inFlight && !this.slots[this.active].inFlight ? this.active : standby) as 0 | 1;
    if (!force && this.slots[this.active].uri === uri && this.slots[this.active].ready) {
      this.emit(false); this.reconcile();
      if (upcoming && upcoming !== uri) void this.load((1 - this.active) as 0 | 1, upcoming);
      return;
    }
    this.emit(true);
    this.timer = setTimeout(() => {
      if (requested === this.version && !this.disposed) this.reportError(true);
    }, this.timeoutMs);
    await this.load(this.active, uri, force);
    if (this.disposed || requested !== this.version || this.failed) return;
    clearTimeout(this.timer);
    if (!this.slots[this.active].ready) { this.reportError(); return; }
    this.emit(false); this.reconcile();
    if (upcoming && upcoming !== uri) void this.load((1 - this.active) as 0 | 1, upcoming);
  }
  setRate(rate: 1 | 2) {
    if (!this.disposed) { this.rate = rate; this.reconcile(); }
  }
  seekTo(seconds: number) {
    if (!this.disposed && Number.isFinite(seconds) && seconds >= 0) this.drivers[this.active].seekTo?.(seconds);
  }
  reportError(timedOut = false) {
    if (this.disposed) return;
    this.failed = true; clearTimeout(this.timer); this.silenceAll();
    this.emit(false, timedOut ? 'The video picture is taking too long. Retry this clip or keep scrolling.' : 'This clip could not load. Retry it or keep scrolling.', timedOut);
  }
  preload(uri?: string) {
    if (!this.disposed && !this.failed && this.slots[this.active].ready && uri && uri !== this.slots[this.active].uri) void this.load((1 - this.active) as 0 | 1, uri);
  }
  dispose() { if (this.disposed) return; this.disposed = true; this.version++; clearTimeout(this.timer); this.slots.forEach(slot => slot.version++); this.silenceAll(true); this.drivers.forEach(driver => driver.dispose?.()); }
}
