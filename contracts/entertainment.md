# Entertainment catalog contract

Owner: Adi. Consumer: recommendations and mobile.

## EntertainmentVideo

Required fields:

| Field | Type | Meaning |
|---|---|---|
| schema_version | "1" | Contract version |
| video_id | string | Stable internal catalog ID |
| provider | tiktok / instagram / fixture | Acquisition source |
| provider_video_id | string | Original provider identifier |
| source_url | HTTPS URL or null | Original post link |
| creator | object | handle, display_name, attribution_url; nullable subfields |
| caption | string | Plain text, possibly empty |
| duration_seconds | number or null | Known measured/provider duration |
| playback | PlaybackSource | Verified player input, below |
| thumbnail_url | HTTPS URL or null | Optional preview |
| acquired_at | timestamp | Retrieval/cache timestamp |
| availability | ready / unavailable / needs_refresh | Feed eligibility |
| acquisition_mode | live / cached / fixture | Honest demo provenance |

PlaybackSource:

- kind: mp4 / hls / embed.
- asset_id: stable string.
- url: HTTPS playback URL.
- expires_at: timestamp or null.
- mime_type: string or null.
- headers_ref: server-only optional reference, never raw cookies in a client payload.

The normalized mobile feed must contain a directly usable URL or supported embed,
without social credentials. If playback requires private headers, provide an
authorized backend-mediated asset route or choose another source. Never expose a
generic arbitrary-URL proxy. Client does not assume embed behaves like native MP4.

## Adapter

list_candidates(cursor, limit) → items + next_cursor.
resolve_playback(video_id, app_user) → PlaybackSource.
refresh_catalog() → job reference and summary.

Provider sessions are implementation details. Deduplicate by provider and
provider_video_id. Empty, unavailable and blocked results are typed outcomes,
not infinite retry loops.

## Initial API

- GET /v1/entertainment/feed?cursor=&limit= → items of EntertainmentVideo + next_cursor.
- GET /v1/entertainment/videos/{video_id}/playback → PlaybackSource.

Both require app authentication. Limit is bounded server-side.
This temporary endpoint lets Adi deliver the first milestone without the learning
engine. Later /v1/feed wraps these records with feed occurrence IDs.

## Acceptance fixture

Include playable ready metadata, expired URL, duplicate provider item, unknown
duration and unavailable clip. Fixture URLs must be explicitly demo assets, with
no embedded credentials. Do not commit actual downloaded video bytes.

## Owned bounded-cache implementation — November 14, 2026

CatalogService accepts a repository with read_items(verified_app_user), allowing
explicit fixtures, a locally owner-bound saved batch, or an injected Atlas cache.
The initial cache is finite, not a live personalized provider paging service.
No provider login/session is stored by the local retrieval probe.

Feed limit is 1–20. Opaque HMAC cursors bind user, limit and batch revision. Invalid
or foreign cursors return 422 INVALID_CURSOR; replaced batches return 409
STALE_CURSOR. An empty eligible window may retain next_cursor; consumers can
continue bounded fetching. Expiry filtering preserves raw offsets to avoid
omitting/duplicating later records when a URL expires between requests.

Playback resolution returns 404 for an unknown/inaccessible record, 410
PLAYBACK_UNAVAILABLE for expired/unavailable/embed-only records, and retryable 503
for storage/provider dependency failures. This cache cannot renew provider URLs;
a successful new acquisition must replace it. Saved-URL retries are retries of the
same link, not renewal. There are no automatic login/checkpoint retries.

Private Atlas batches have one verified owner, at most 100 normalized records,
32 KiB per record, and 60–86400 second retention. Atomic replacement prevents
partial-page publication. Reads enforce expiry without waiting for TTL deletion.
Server-only cursor signing material is injected by core and must match across
replicas. Private cache fields never include raw provider sessions/headers.
See database/domains/entertainment and the proposed bootstrap decision.
