export interface CacheStorage { readOwner(): Promise<string | null>; writeOwner(owner: string | null): Promise<void>; clear(): Promise<void> }
/** Serialize account transitions; disk bytes are reusable only after matching the
 * authenticated owner/API scope. Failure falls back to uncached network playback. */
export class MediaCachePolicy {
  private queue: Promise<unknown> = Promise.resolve();
  constructor(private storage: CacheStorage) {}
  prepare(owner: string | null): Promise<boolean> {
    const work = this.queue.then(async () => {
      try {
        const previous = await this.storage.readOwner();
        if (!owner || previous !== owner) await this.storage.clear();
        await this.storage.writeOwner(owner);
        return !!owner;
      } catch { return false; }
    });
    this.queue = work; return work;
  }
}
