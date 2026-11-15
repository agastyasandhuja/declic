import type { ApiClient } from '../../lib/api/client';
import type { FeedEventBuffer } from './FeedEventBuffer';

/** Rewind is an explicit zero-credit server anchor, never disguised progress. */
export async function seekFeedVideo(input: {
  api: ApiClient; events: Pick<FeedEventBuffer, 'flush'>;
  sessionId: string; itemId: string; eventId: string; positionMs: number; visibleWatchMs: number;
  isActive(): boolean; isCurrent(): boolean; onSeek(): void | Promise<void>;
}) {
  await input.events.flush();
  if (!input.isActive()) return false;
  const result = await input.api.request<{accepted_event_ids: string[]; rejected: {event_id: string; code: string}[]}>('/v1/feed/events', {
    method: 'POST', headers: { 'Idempotency-Key': input.eventId }, body: [{
      event_id: input.eventId, session_id: input.sessionId, item_id: input.itemId,
      event_type: 'playback_seeked', client_occurred_at: new Date().toISOString(),
      payload: { position_ms: Math.round(input.positionMs), visible_watch_ms: Math.round(input.visibleWatchMs) },
    }],
  });
  if (!result.accepted_event_ids.includes(input.eventId)) throw new Error('Unable to seek yet. Resume playback and try again.');
  if (!input.isCurrent()) return false;
  await input.onSeek(); return true;
}


/** Expo updates currentTime asynchronously. Leave progress paused until it lands. */
export async function waitForNativeSeek(
  target: number, getPosition: () => number, isCurrent: () => boolean,
  wait = () => new Promise<void>(resolve => setTimeout(resolve, 50)),
) {
  for (let attempt = 0; attempt < 40; attempt++) {
    if (!isCurrent()) return false;
    if (Math.abs(getPosition() - target) <= 0.1) return true;
    await wait();
  }
  return false;
}
