import type { PlaybackSource } from '../../contracts/generated';
import { ApiError } from '../../lib/api/client';
import type { BufferedPlayerController } from '../../lib/playback/BufferedPlayerController';
import { needsPlaybackRefresh } from '../../lib/playback/PlaybackRecovery';

export type UpcomingPlaybackUpdate = { kind: 'remove' } | { kind: 'refresh'; playback: PlaybackSource };

export function isUnavailablePlayback(error: unknown) {
  return error instanceof ApiError &&
    ((error.status === 404 && ['VIDEO_NOT_FOUND', 'CATALOG_NOT_FOUND'].includes(error.code)) ||
     (error.status === 410 && error.code === 'PLAYBACK_UNAVAILABLE'));
}

export async function prepareUpcomingPlayback(
  source: Pick<PlaybackSource, 'url' | 'expires_at'>,
  controller: Pick<BufferedPlayerController, 'preload'>,
  resolve: (signal: AbortSignal) => Promise<PlaybackSource>,
  signal: AbortSignal,
): Promise<UpcomingPlaybackUpdate | undefined> {
  if (signal.aborted) return;
  const stale = needsPlaybackRefresh(source.expires_at);
  // Healthy URLs go straight to the standby player. Instagram renewal is rate limited.
  if (!stale && await controller.preload(source.url) !== 'failed') return;
  if (signal.aborted) return;
  try {
    const fresh = await resolve(signal);
    if (!signal.aborted && !needsPlaybackRefresh(fresh.expires_at) &&
        (fresh.url !== source.url || (stale && fresh.expires_at !== source.expires_at))) {
      return { kind: 'refresh', playback: fresh };
    }
  } catch (error) {
    if (!signal.aborted && isUnavailablePlayback(error)) {
      return { kind: 'remove' };
    }
  }
}

/** Change only unseen cards, even if a swipe or a page refill raced the resolver. */
export function updateUpcomingPlayback<T>(
  queue: T[],
  index: number,
  expected: T,
  update: UpcomingPlaybackUpdate,
  replace: (item: T, playback: PlaybackSource) => T,
) {
  const target = queue.indexOf(expected, index + 1);
  if (target < 0) return queue;
  const next = queue.slice();
  if (update.kind === 'remove') next.splice(target, 1);
  else next[target] = replace(expected, update.playback);
  return next;
}
