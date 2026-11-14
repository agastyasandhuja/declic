export interface PlayerDriver { play(): void; pause(): void; replaceAsync(uri: string): Promise<void>; seekTo?(seconds: number): void; setRate?(rate: number): void; setMuted?(muted: boolean): void }
export interface PlaybackState { loading: boolean; ready: boolean; error: string | null }
export interface PlaybackGate { foreground: boolean; focused: boolean; manuallyPaused: boolean }

// One driver owns all media. Source replacement is serialized so a slow older
// load cannot replace a newer swipe or restart playback after backgrounding.
export class SinglePlayerController {
  private version = 0;
  private disposed = false;
  private ready = false;
  private gate: PlaybackGate = { foreground: true, focused: true, manuallyPaused: false };
  private queue: Promise<void> = Promise.resolve();
  constructor(private driver: PlayerDriver, private onState: (state: PlaybackState) => void) {}
  setGate(patch: Partial<PlaybackGate>) { this.gate = { ...this.gate, ...patch }; this.reconcile(); }
  private reconcile() {
    if (!this.disposed && this.ready && this.gate.foreground && this.gate.focused && !this.gate.manuallyPaused) this.driver.play();
    else this.driver.pause();
  }
  setSource(uri: string): Promise<void> {
    const requested = ++this.version;
    this.ready = false; this.driver.pause(); this.onState({ loading: true, ready: false, error: null });
    this.queue = this.queue.catch(() => undefined).then(async () => {
      if (this.disposed || requested !== this.version) return;
      try {
        await this.driver.replaceAsync(uri);
        if (this.disposed || requested !== this.version) return;
        this.ready = true;
        this.onState({ loading: false, ready: true, error: null });
        this.reconcile();
      } catch {
        if (!this.disposed && requested === this.version) this.reportError();
      }
    });
    return this.queue;
  }
  reportError() {
    this.ready = false; this.driver.pause();
    if (!this.disposed) this.onState({ loading: false, ready: false, error: 'This clip could not load. Retry it or keep scrolling.' });
  }
  dispose() { this.disposed = true; this.version++; this.ready = false; this.driver.pause(); }
}
