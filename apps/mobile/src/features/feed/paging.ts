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

/** Follow at most four empty windows and retry short server pacing twice. */
export async function fetchAvailablePage(source: FeedSource, previous: EntertainmentVideo[], cursor: string | null,
  signal: AbortSignal, checkpoint: (cursor: string | null) => void, wait = abortableDelay) {
  const seen = new Set(cursor ? [cursor] : []);
  let busyRetries = 0;
  for (let empty = 0; ; empty++) {
    let page;
    for (;;) {
      if (signal.aborted) throw new Error('Cancelled');
      try { page = await source.getPage(cursor, signal); break; }
      catch (error) {
        if (!(error instanceof ApiError) || error.code !== 'INSTAGRAM_BUSY' || !error.retryable || error.status !== 503 || busyRetries >= 2) throw error;
        busyRetries++;
        await wait(Math.max(2000, Math.min(10000, error.retryAfterMs ?? 2000)), signal);
      }
    }
    if (page.next_cursor && seen.has(page.next_cursor)) throw new Error('The feed repeated a page. Reload to recover.');
    if (!page.next_cursor || unseenVideos(previous, page.items).length > 0) return page;
    seen.add(page.next_cursor);
    cursor = page.next_cursor;
    checkpoint(cursor); // Preserve progress even if the next request fails.
    if (empty >= 3) return page;
  }
}
