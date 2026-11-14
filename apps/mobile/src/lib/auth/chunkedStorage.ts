export interface AsyncKeyValueStore {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

interface Manifest { version: 1; id: string; count: number }

// Only the small manifest is replaced on commit. Failed writes preserve the old
// session. Each chunk is <= 400 Unicode code points (<= 1600 UTF-8 bytes).
export function createChunkedStorage(store: AsyncKeyValueStore, nonce: () => string): AsyncKeyValueStore {
  let pending: Promise<unknown> = Promise.resolve();
  function serialized<T>(work: () => Promise<T>): Promise<T> {
    const result = pending.then(work);
    pending = result.catch(() => undefined);
    return result;
  }
  async function manifest(key: string): Promise<Manifest | null> {
    const raw = await store.getItem(key);
    if (!raw) return null;
    const value = JSON.parse(raw) as Manifest;
    if (value.version !== 1 || !/^[a-zA-Z0-9-]+$/.test(value.id) || !Number.isInteger(value.count) || value.count < 1 || value.count > 128) {
      throw new Error('Saved session is unreadable. Please sign in again.');
    }
    return value;
  }
  async function discard(key: string, value: Manifest | null) {
    if (value) await Promise.allSettled(Array.from({ length: value.count }, (_, i) => store.removeItem(`${key}.${value.id}.${i}`)));
  }
  return {
    getItem: key => serialized(async () => {
      const value = await manifest(key);
      if (!value) return null;
      const chunks = await Promise.all(Array.from({ length: value.count }, (_, i) => store.getItem(`${key}.${value.id}.${i}`)));
      if (chunks.some(chunk => chunk === null)) throw new Error('Saved session is incomplete. Please sign in again.');
      return chunks.join('');
    }),
    setItem: (key, value) => serialized(async () => {
      const previous = await manifest(key);
      const points = Array.from(value);
      const chunks = Array.from({ length: Math.max(1, Math.ceil(points.length / 400)) }, (_, i) => points.slice(i * 400, (i + 1) * 400).join(''));
      if (chunks.length > 128) throw new Error('Session exceeds secure storage limits.');
      const next: Manifest = { version: 1, id: nonce(), count: chunks.length };
      try {
        for (let i = 0; i < chunks.length; i++) await store.setItem(`${key}.${next.id}.${i}`, chunks[i]);
        await store.setItem(key, JSON.stringify(next));
      } catch (error) {
        await discard(key, next);
        throw error;
      }
      await discard(key, previous);
    }),
    removeItem: key => serialized(async () => {
      let previous: Manifest | null = null;
      try { previous = await manifest(key); } catch { /* Permit clearing a corrupted manifest. */ }
      await store.removeItem(key);
      await discard(key, previous);
    }),
  };
}
