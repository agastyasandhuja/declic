interface BufferIdentity { generation: number; ready: boolean }
/** A standby frame can be promoted without remounting its native surface. */
export class DecodedFrames {
  private buffers: BufferIdentity[] = [];
  private frames = new Map<number, number>();
  observe(buffers: BufferIdentity[]) {
    this.buffers = buffers;
    for (const [slot, generation] of this.frames) if (!buffers[slot]?.ready || buffers[slot].generation !== generation) this.frames.delete(slot);
  }
  mark(slot: number, generation: number) {
    if (!this.buffers[slot]?.ready || this.buffers[slot].generation !== generation) return false;
    this.frames.set(slot, generation); return true;
  }
  has(slot: number) { return this.buffers[slot]?.ready && this.frames.get(slot) === this.buffers[slot].generation; }
}
