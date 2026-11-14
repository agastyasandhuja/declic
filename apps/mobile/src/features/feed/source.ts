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
  return videos.filter(video => {
    const key = `${video.provider}:${video.provider_video_id}`;
    if (seen.has(key) || video.availability !== 'ready' || video.playback.kind === 'embed' || (video.playback.expires_at && Date.parse(video.playback.expires_at) <= now)) return false;
    seen.add(key); return true;
  });
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
    async resolvePlayback() {
      throw new Error('Saved Instagram links cannot refresh themselves. Run the probe and restart the preview.');
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
