# Instagram session durability and media freshness

Status: implementation audit and proposed long-term integration boundary, November 14, 2026.

The reported failure is clips failing after reopening while the student remains
signed in. Treat app authentication, Instagram authentication and media URL
freshness as separate states.

The native app already persists Supabase sessions in chunked SecureStore and
starts token refresh on foreground. The backend stores an encrypted Instagram
session in Atlas, bound to the verified app user. API/worker reconstruction uses
saved authentication cookies, authorization data and device identity; successful
catalog or playback refresh stores updated settings. App logout does not delete
the Instagram connection. Explicit Instagram disconnect does.

The demo now exposes authenticated `POST /v1/instagram/browser-session` with
`{username, session_id}`. It accepts a single secret cookie value rather than an
arbitrary session object, verifies the canonical Instagram account against the
supplied username, and uses the existing encrypted owner-bound connection store.
No password fallback runs. Verification failures return fixed diagnostics, keep
an existing working connection intact, and cannot reverse a concurrent disconnect.
The mobile UI must hold the cookie only long enough to submit it explicitly and
clear it after success. This is a demo session handoff, not OAuth.

Instagram playback URLs receive a conservative five-minute freshness lease, and
the current catalog snapshot expires after ten minutes. Neither expiry means the
Instagram login has expired. On foreground and early playback failure, the mobile
client should request renewal for the currently owned video, with bounded retries
and cancellation when selection changes. If catalog cleanup or replacement has
removed that video, reload the feed. Do not reinterpret `VIDEO_NOT_FOUND`, a
temporary upstream failure, or a rate limit as a request to reconnect Instagram.
Only a provider authentication/checkpoint rejection warrants that action. Server
renewal must continue looking up the owned catalog entry rather than trusting a
caller-supplied Instagram media identifier.

Keep the worker available while the Mac hosts the demo. If it stops, fresh feed
inventory cannot be promised even though authentication persists. The standalone
local preview is a separate process with an in-memory feed and owner-only session
file; its pagination fixes do not create an official renewable Instagram token.
Browser-session reuse remains dependent on Instagram accepting that session;
neither cookie persistence nor SDK restoration guarantees its lifetime.

For a supported long-term integration, Meta's Instagram Login API targets
professional Business/Creator accounts and their own media, comments, insights,
mentions and messaging. These documented capabilities do not provide a personal
account's recommendation feed; replacing the demo with this API requires an
explicit product change to authorized creator/owned content. [Meta API overview](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login)

For that professional-account product, use OAuth authorization-code exchange,
encrypted server-side tokens and scheduled refresh before expiry. Meta documents
60-day long-lived tokens and a refresh endpoint; advanced access is required for
professional accounts the app operator does not own/manage. This is a future
integration proposal, not implemented or live-validated behavior. [Meta Business Login](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login)

Offline regression checks reconstruct the pinned Instagram SDK from serialized
synthetic cookies/device settings with network connections prohibited, and reopen
the application database/vault using the same encryption key. Media tests cover
expired URLs/catalogs, transient failures preserving authentication, and catalog
eviction requiring feed reload. These tests establish local persistence mechanics,
not continued acceptance of real sessions by Instagram.
