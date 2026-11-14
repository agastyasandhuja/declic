import catalog from '../../../../../fixtures/entertainment/feed.json';
import { parseFeedPage, parsePlayback } from '../../contracts/validate';
import type { EntertainmentFeedPage, EntertainmentVideo, PlaybackSource } from '../../contracts/generated';
import type { ApiClient } from '../../lib/api/client';

export interface FeedSource {
  mode: 'fixture' | 'api' | 'saved_instagram';
  getPage(cursor?: string | null, signal?: AbortSignal): Promise<EntertainmentFeedPage>;
  resolvePlayback(videoId: string): Promise<PlaybackSource>;
}
export function eligibleVideos(videos: EntertainmentVideo[], now = Date.now()) {
  const seen = new Set<string>();
  const ids = new Set<string>();
  return videos.filter(video => {
    const key = `${video.provider}:${video.provider_video_id}`;
    if (seen.has(key) || ids.has(video.video_id) || video.availability !== 'ready' || video.playback.kind === 'embed' || (video.playback.expires_at && Date.parse(video.playback.expires_at) <= now)) return false;
    seen.add(key); ids.add(video.video_id); return true;
  });
}

export function unseenVideos(previous: EntertainmentVideo[], incoming: EntertainmentVideo[]) {
  const keys = new Set(previous.map(video => `${video.provider}:${video.provider_video_id}`));
  const ids = new Set(previous.map(video => video.video_id));
  return eligibleVideos(incoming.filter(video => !keys.has(`${video.provider}:${video.provider_video_id}`) && !ids.has(video.video_id)));
}
export function appendFeedPage(previous: EntertainmentVideo[], incoming: EntertainmentVideo[]) {
  // Keep existing card indexes stable when an old signed URL expires during pagination.
  return [...previous, ...unseenVideos(previous, incoming)].slice(0, 100);
}
export function appendFeedWindow(previous: EntertainmentVideo[], incoming: EntertainmentVideo[], activeIndex: number, capacity = 100) {
  if (!Number.isInteger(capacity) || capacity < 5 || !Number.isInteger(activeIndex) || activeIndex < 0 || (previous.length && activeIndex >= previous.length)) throw new Error('Invalid feed window.');
  const combined = [...previous, ...unseenVideos(previous, incoming)];
  // Evict only already-passed cards, preserving the current clip and every unseen clip.
  const removed = Math.min(Math.max(0, combined.length - capacity), activeIndex);
  if (combined.length - removed > capacity) throw new Error('Watch a few more clips before loading another page.');
  return { items: combined.slice(removed), index: activeIndex - removed, removed };
}
export function shouldPrefetchPage({ index, count, hasNext, focused, foreground, loading, hasError }: {
  index: number; count: number; hasNext: boolean; focused: boolean; foreground: boolean; loading: boolean; hasError: boolean;
}) {
  return count > 0 && count - index - 1 < 8 && hasNext && focused && foreground && !loading && !hasError;
}
export function createFixtureSource(): FeedSource {
  const items = eligibleVideos(parseFeedPage(catalog).items);
  return {
    mode: 'fixture',
    async getPage(cursor) {
      if (cursor && !/^fixture:\d+$/.test(cursor)) throw new Error('Invalid demo cursor. Reload the feed.');
      const offset = cursor ? Number(cursor.split(':')[1]) : 0;
      const end = offset + 3;
      return { schema_version: '1', items: items.slice(offset, end), next_cursor: end < items.length ? `fixture:${end}` : null };
    },
    async resolvePlayback(videoId) {
      const item = items.find(video => video.video_id === videoId);
      if (!item) throw new Error('This demo clip is unavailable.');
      return item.playback;
    },
  };
}
export function createSavedInstagramSource(value: unknown): FeedSource {
  const page = parseFeedPage(value);
  const items = eligibleVideos(page.items).filter(item => item.provider === 'instagram');
  return {
    mode: 'saved_instagram',
    async getPage(cursor) {
      if (cursor) throw new Error('This saved Instagram preview has one batch. Fetch a new catalog for more clips.');
      return { schema_version: '1', items, next_cursor: null };
    },
    async resolvePlayback(videoId) {
      const item = items.find(video => video.video_id === videoId);
      if (!item || (item.playback.expires_at && Date.parse(item.playback.expires_at) <= Date.now())) throw new Error('This saved link is unavailable. Retrieve a fresh catalog on the Mac.');
      // Retry the same saved URL after a transient network failure; never imply renewal.
      return item.playback;
    },
  };
}
export function createApiFeedSource(api: ApiClient): FeedSource {
  return {
    mode: 'api',
    async getPage(cursor, signal) {
      const query = new URLSearchParams({ limit: '5' });
      if (cursor) query.set('cursor', cursor);
      return parseFeedPage(await api.request(`/v1/entertainment/feed?${query}`, { signal }));
    },
    async resolvePlayback(videoId) {
      return parsePlayback(await api.request(`/v1/entertainment/videos/${encodeURIComponent(videoId)}/playback`));
    },
  };
}

/** Session-scoped watch history survives feed reloads and rolling-window eviction.
 * Only identities are retained, never provider URLs or session credentials. */
export class FeedHistory {
  private keys = new Set<string>();
  constructor(private capacity = 2048) {}
  private key(video: EntertainmentVideo) { return `${video.provider}:${video.provider_video_id}`; }
  remember(video: EntertainmentVideo) {
    const key = this.key(video); this.keys.delete(key); this.keys.add(key);
    while (this.keys.size > this.capacity) this.keys.delete(this.keys.values().next().value!);
  }
  unseen(videos: EntertainmentVideo[]) { return videos.filter(video => !this.keys.has(this.key(video))); }
}
