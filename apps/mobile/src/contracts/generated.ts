// Generated from contracts/schemas by npm run contracts:generate. Do not edit.
export interface CurrentUser {
  user_id: string;
  email: string | null;
  display_name: string | null;
  timezone: string;
  created_at: string;
  [k: string]: unknown;
}

export interface EntertainmentFeedPage {
  schema_version: "1";
  items: EntertainmentVideo[];
  next_cursor: string | null;
}
/**
 * This interface was referenced by `EntertainmentFeedPage`'s JSON-Schema
 * via the `definition` "EntertainmentVideo".
 */
export interface EntertainmentVideo {
  schema_version: "1";
  video_id: string;
  provider: "tiktok" | "instagram" | "fixture";
  provider_video_id: string;
  source_url: string | null;
  creator: {
    handle: string | null;
    display_name: string | null;
    attribution_url: string | null;
  };
  caption: string;
  like_count?: number | null;
  comment_count?: number | null;
  duration_seconds: number | null;
  playback: PlaybackSource;
  thumbnail_url: string | null;
  acquired_at: string;
  availability: "ready" | "unavailable" | "needs_refresh";
  acquisition_mode: "live" | "cached" | "fixture";
}
/**
 * This interface was referenced by `EntertainmentFeedPage`'s JSON-Schema
 * via the `definition` "PlaybackSource".
 */
export interface PlaybackSource {
  kind: "mp4" | "hls" | "embed";
  asset_id: string;
  url: string;
  expires_at: string | null;
  mime_type: string | null;
}
