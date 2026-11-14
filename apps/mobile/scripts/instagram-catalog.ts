import type { EntertainmentFeedPage, EntertainmentVideo } from '../src/contracts/generated';
import { parseFeedPage } from '../src/contracts/validate';

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid Instagram catalog object.');
  return value as Record<string, unknown>;
}

export function normalizeInstagramCatalog(input: unknown): EntertainmentFeedPage {
  const catalog = record(input);
  if (typeof catalog.acquired_at !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(catalog.acquired_at) || !Number.isFinite(Date.parse(catalog.acquired_at)) || !Array.isArray(catalog.items)) {
    throw new Error('The Instagram catalog needs a zoned acquisition timestamp and items.');
  }
  const acquired = catalog.acquired_at;
  const seen = new Set<string>();
  const items: EntertainmentVideo[] = [];
  for (const value of catalog.items) {
    const item = record(value);
    if (typeof item.provider_video_id !== 'string' || !/^\d+$/.test(item.provider_video_id) || typeof item.creator_handle !== 'string' || !/^[A-Za-z0-9_.]+$/.test(item.creator_handle) || typeof item.caption !== 'string' || typeof item.duration_seconds !== 'number' || !Number.isFinite(item.duration_seconds) || item.duration_seconds < 0) {
      throw new Error('A saved Instagram record has invalid required metadata.');
    }
    if (typeof item.source_url !== 'string' || typeof item.candidate_playback_url !== 'string') throw new Error('A saved Instagram record has no video URL. Fetch a fresh catalog.');
    const source = new URL(item.source_url);
    const playback = new URL(item.candidate_playback_url);
    if (source.protocol !== 'https:' || !['www.instagram.com', 'instagram.com'].includes(source.hostname) || !source.pathname.startsWith('/reel/') || source.username || source.password || playback.protocol !== 'https:' || !playback.hostname.endsWith('.cdninstagram.com') || playback.username || playback.password) {
      throw new Error('Saved Instagram URLs must use Instagram posts and its HTTPS video CDN.');
    }
    if (seen.has(item.provider_video_id)) continue;
    seen.add(item.provider_video_id);
    items.push({
      schema_version: '1', video_id: `instagram_${item.provider_video_id}`, provider: 'instagram', provider_video_id: item.provider_video_id,
      source_url: source.toString(), creator: { handle: item.creator_handle, display_name: `@${item.creator_handle}`, attribution_url: `https://www.instagram.com/${item.creator_handle}/` },
      caption: item.caption, duration_seconds: item.duration_seconds,
      playback: { kind: 'mp4', asset_id: `instagram:${item.provider_video_id}:mp4`, url: playback.toString(), expires_at: null, mime_type: 'video/mp4' },
      thumbnail_url: null, acquired_at: acquired, availability: 'ready', acquisition_mode: 'cached',
    });
  }
  if (!items.length) throw new Error('No saved Instagram clips. Run the local probe first.');
  return parseFeedPage({ schema_version: '1', items, next_cursor: null });
}
