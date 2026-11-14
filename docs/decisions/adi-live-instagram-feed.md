# Owner-bound live Instagram demo adapter

Status: proposed shared integration; implemented within Adi's entertainment/mobile
ownership. November 14, 2026. Live account pagination and phone acceptance remain
unverified until the local connection and device checks complete.

## Decision and integration impact

The user requested fresh Instagram retrieval instead of the four saved Reels.
Keep the existing v1 entertainment feed/playback routes and wire schema. Add an
optional instagrapi 3.2.12 provider and a LiveInstagramCatalog behind those routes.
Agastya still owns the shared main.py, runtime dependencies and deployment.
The existing local experiment factory can assemble this adapter for development;
it does not create a second production API or a new infrastructure service.

This adapter is separate from the finite Atlas entertainment_catalogs snapshot.
No Atlas validator, collection, migration or existing cache capacity is changed.
Page continuation, short retry caches and recently issued playback metadata are
process-local for the single-account demo. Cross-process/distributed persistence
is future integration work, not an implied capability of the snapshot repository.

## Connection and access

A trusted local CLI binds the session to a canonical Supabase user UUID, obtained
through local app sign-in or explicitly copied from the signed-in app by the
operator. It performs one explicit Instagram SDK login and saves only allowlisted
session/device settings in an ignored owner-only file. It never saves passwords
or app access tokens. This is not a public social-login/token-collection API.

The API restores that session without logging in again. Every feed/playback read
first verifies the app bearer and checks the bound owner. Another user cannot
fetch the account's feed or force an Instagram request. Clients receive selected
metadata and credential-free HTTPS CDN URLs; provider session material and raw
provider cursors never leave the server. No likes, follows, posting, downloads or
explicit Instagram watch/seen-state writes are introduced.

After an observed login-verification interruption, the local helper also saves a
pending device profile before network login. The same owner/login hash restores
the same device IDs and SDK device-registration signing key for manual attempts.
These private profiles retain device/CSRF cookies; authentication cookies, authorization data and passwords are
excluded. They are not ready API connections. Official-app verification stays
with the user; no automatic checkpoint resolution or login loop is introduced.

The local login helper prompts only after a supported account-2FA challenge, selects
the delivery method before requesting an SMS code, and submits at most one code
against the existing server-issued context. Unsupported continuations stop. A
bounded current-user read must verify the new identity before ready-session
publication. Fixed request-phase labels/statuses provide redacted diagnostics;
raw login payloads, contexts and codes are never logged or persisted. The wrapper
bypasses the SDK's timeout retry loops and caps/rejects repeated password
endpoint calls. These changes stay within local operator setup, not mobile auth
or shared API core.

The observed SDK CAA-to-legacy fallback tried to repeat the CAA password request
while the owner reported receiving an SMS. No supported 2FA continuation reached
the helper. Optional --browser-session instead restores a session explicitly
copied by the owner from their own official browser login, using the documented
SDK login_by_sessionid method. Input stays at a local hidden prompt; no cookie
value is accepted as an argument or sent to mobile. Password requests are refused
in this mode. A canonical current-user read must match the entered Instagram
username before saving a ready session. Private API compatibility remains a live
check, not an assumed property of a signed-in browser.

## Paging and recovery

- One provider request per new server page, retaining the remainder when the
  provider returns more than the requested 1–20 client items. Mobile requests five.
- HMAC continuations bind owner, feed generation, page number and page size.
  A retry replays its cached page. Expired/evicted/restarted cursors return 409
  STALE_CURSOR. Sessions last 30 minutes; repeated root GETs reuse a root for 30s.
- Memory bounds: 100 pending + 100 recently issued records, 20 page-reference
  entries, 2048 deduplication IDs and 128 provider-cursor hashes per connection.
  Mobile keeps at most 100 records and evicts only already-passed cards.
  Metadata refill targets eight upcoming clips, while native playback retains
  only its active player and paused next buffer. Duplicate-only page traversal
  is paced, with two BUSY retries per page and two additional temporary-outage
  retries per four-page window. Three windows (12 consecutive empty pages) are
  the automatic refill bound, with pauses between successful duplicate windows.
  Provider rate limits/auth errors are not polled; long waits require manual retry.

- SDK feed/media calls use one pinned low-level request. The high-level helper
  can swallow errors and private_request can sleep/retry for 60 seconds, so neither
  is used for these reads. TLS is verified, redirects disabled and transport
  timeouts bounded. No automatic login or checkpoint resolution occurs.
- Requests have a two-second minimum provider interval, a 30-second transient
  failure cooldown and a five-minute rate-limit cooldown. A checkpoint/login
  rejection pauses provider reads until the operator reconnects and restarts.
  Already loaded playable clips remain available.
- Playback resolution only refreshes known recently issued IDs. A conservative
  five-minute metadata freshness deadline triggers re-resolution; it is not a
  claim that Instagram guarantees that URL lifetime. Refresh retries are coalesced
  for 30s. Unknown/foreign IDs never trigger a provider lookup.

The local live factory can write aggregate runtime diagnostics in the ignored
private setup directory. This optional callback contains only counts/fixed states,
never account/media identity, raw provider data or credentials. It adds no API
route or service and is not required by shared-core assembly. Diagnostic failure
cannot fail an authorized feed response.

## Local and shared handoff

See [live setup](../ADI_INSTAGRAM_LIVE.md). Run one API process. The local factory
closes SDK transports on shutdown. Shared assembly should inject one owned catalog
instance and register the existing router using its authenticated CurrentUser
dependency; map CatalogFailure to the common safe error envelope. The domain
service's list_candidates(user, cursor, limit) is not a drop-in replacement for
core's separate EntertainmentReader.list_candidates(user_id, limit) protocol.
Agastya owns that candidate-model composition and must not guess the signatures.

No private Expo tunnel is enabled by this change. The existing preview decision's
specific-approval requirement for forwarding private metadata/app bearer tokens
through a public Expo development tunnel remains in effect. An existing trusted
HTTPS API origin can be configured normally. Redirect fixes and custom SMTP remain
deferred by the user for the demo.
