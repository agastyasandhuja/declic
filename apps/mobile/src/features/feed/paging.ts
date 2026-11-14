import { ApiError } from '../../lib/api/client';
import type { EntertainmentVideo } from '../../contracts/generated';
import type { FeedSource } from './source';
import { unseenVideos } from './source';

export function abortableDelay(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) { reject(new Error('Cancelled')); return; }
    const abort = () => { clearTimeout(timer); reject(new Error('Cancelled')); };
    const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve(); }, ms);
    signal.addEventListener('abort', abort, { once: true });
  });
}

/** One traversal shares a transient budget; each page gets two short pacing waits. */
export function createPageReader(signal: AbortSignal, wait = abortableDelay) {
  let transientRetries = 0;
  return async function read<T>(request: () => Promise<T>): Promise<T> {
    let busyRetries = 0;
    for (;;) {
      if (signal.aborted) throw new Error('Cancelled');
      try { return await request(); }
      catch (error) {
        if (!(error instanceof ApiError) || !error.retryable) throw error;
        if (error.code === 'INSTAGRAM_BUSY' && error.status === 503 && busyRetries < 2) {
          if ((error.retryAfterMs ?? 0) > 10000) throw error;
          busyRetries++;
          await wait(Math.max(2000, Math.min(10000, error.retryAfterMs ?? 2000)), signal);
        } else if (transientRetries < 2 && ((error.status === 0 && error.code === 'NETWORK_ERROR') ||
          (error.status === 503 && ['PREVIEW_UNAVAILABLE', 'INSTAGRAM_UNAVAILABLE'].includes(error.code)))) {
          if ((error.retryAfterMs ?? 0) > 30000) throw error;
          const fallback = error.code === 'INSTAGRAM_UNAVAILABLE' ? 30000 : 1000 * 2 ** transientRetries;
          transientRetries++;
          await wait(Math.max(1000, Math.min(30000, error.retryAfterMs ?? fallback)), signal);
        } else throw error;
      }
    }
  };
}

/** Bounded traversal: per-page pacing retries plus two transient retries overall. */
export async function fetchAvailablePage(source: FeedSource, previous: EntertainmentVideo[], cursor: string | null,
  signal: AbortSignal, checkpoint: (cursor: string | null) => void, wait = abortableDelay) {
  const seen = new Set(cursor ? [cursor] : []);
  const read = createPageReader(signal, wait);
  for (let empty = 0; ; empty++) {
    const page = await read(() => source.getPage(cursor, signal));
    if (page.next_cursor && seen.has(page.next_cursor)) throw new Error('The feed repeated a page. Reload to recover.');
    if (!page.next_cursor || unseenVideos(previous, page.items).length > 0) return page;
    seen.add(page.next_cursor);
    cursor = page.next_cursor;
    checkpoint(cursor); // Preserve progress even if the next request fails.
    if (empty >= 3) return page;
    // A duplicate-only response may still have a valid continuation. Pace the
    // next provider read instead of provoking a 503 and spending retry budget.
    if (source.mode === 'api') await wait(2000, signal);
  }
}

/** Continue successful duplicate-only windows twice before requiring user action. */
export async function fetchRefillPage(source: FeedSource, previous: EntertainmentVideo[], cursor: string | null,
  signal: AbortSignal, checkpoint: (cursor: string | null) => void, wait = abortableDelay) {
  for (let window = 0; ; window++) {
    const page = await fetchAvailablePage(source, previous, cursor, signal, checkpoint, wait);
    if (!page.next_cursor || unseenVideos(previous, page.items).length > 0 || source.mode !== 'api' || window >= 2) return page;
    cursor = page.next_cursor;
    await wait((window + 1) * 2000, signal);
  }
}
