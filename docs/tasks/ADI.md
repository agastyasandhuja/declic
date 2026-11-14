# Adi — mobile experience, app identity, entertainment

## Read first

[Root instructions](../../AGENTS.md), [project](../PROJECT.md),
[identity contract](../../contracts/identity.md),
[entertainment contract](../../contracts/entertainment.md),
[feed contract](../../contracts/feed.md), and [integration plan](../INTEGRATION.md).

## Mission

Your FIRST goal is a working iPhone app: signup, login, and smooth short-form
entertainment scrolling. No Canvas connection, syllabus upload, Gemini call,
quiz integration, or generated lesson is required for that first milestone.
App login is independent of any TikTok/Instagram or Canvas login.

## You own

- All of apps/mobile, including navigation, app-wide state, visual system,
  authentication UI, player, feed UI, networking, assets and app configuration.
- services/api/app/modules/auth and modules/entertainment.
- contracts/identity.md and entertainment.md.
- fixtures/identity and fixtures/entertainment.
- database/domains/identity and database/domains/entertainment.
- Root JS workspace/package configuration and shared JS lockfile.
- Your status file at docs/status/ADI.md.

Do not edit Amogh's feature package or Agastya's learning engine. You integrate
their exported React Native components into the app shell. Coordinate shared
Python dependencies and API router registration with Agastya.

## Milestone A1 — app and identity

1. Initialize React Native + Expo + TypeScript inside apps/mobile.
2. Keep the repository root as a workspace, not the Expo application itself.
3. Set up minimal auth and feed navigation with clear loading/error states.
4. Implement Supabase Auth signup/login/logout and persistence using
   current provider guidance. Show email confirmation when required.
5. Keep session credentials in secure device storage; never store passwords.
6. Define one API client that attaches app access tokens and handles expired sessions.
7. Add a fixture entertainment adapter so player work proceeds independently.
8. Document exact install/start/device-test commands and public environment names.

Application profiles and entertainment metadata use MongoDB Atlas under the
[accepted storage decision](../decisions/001-proposed-atlas-application-data.md).
Prepare Adi's collection/validator/index drafts in the owned database domains;
Agastya integrates the shared connection and ordered database changes. Keep Atlas
credentials server-side. Mobile uses Supabase Auth and the authenticated API;
fixture playback does not depend on a live database.

Acceptance:

- New account can be created and a returning user can log in.
- Invalid credentials and network loss produce usable messages.
- Restart preserves a valid session; logout clears local private state.
- Feed is accessible without Canvas.
- API rejects missing/invalid app tokens; caller cannot choose another user ID.

### A1 implementation cross-reference — November 14, 2026

A1 code and independent backend tests are implemented; **live acceptance remains
open**. See [current delivery evidence](../status/ADI.md#current-a1a3-delivery--november-14-2026)
for commands, fixtures versus live results, and the remaining device checks.

| A1 item | Implementation and evidence | Remaining acceptance |
|---|---|---|
| 1–2. Expo/RN/TS in apps/mobile; root workspace | Native simulator launch, strict TypeScript, Expo Doctor and iOS export pass. | Production signing is outside A1. |
| 3. Auth/feed navigation and recovery | Native loading, manual pause, route pause, unavailable skip, empty recovery; API/asset deadlines. | Physical-phone sustained swipe/network-loss check. |
| 4. Supabase signup/login/logout/persistence | SDK signup/login/email-confirmation UX and app-wide restoration. User reported real account creation/email/login on the phone. | Controlled restart, logout/private-state clearing, invalid credentials/offline on device. |
| 5. Secure device sessions | SecureStore chunking, torn-write/Unicode tests and explicit corrupted-session clearing. No password persistence. | Actual authenticated device restart/logout. |
| 6. Shared authenticated client and server adapter | HTTPS-only bearer client, safe refresh/replay and body deadline. SupabaseVerifier plus identity router; missing/forged tokens and ownership tested. Real configured Supabase rejected an invalid token with 401. | Successful real-account protected API call and shared-core route assembly. |
| 7. Fixture entertainment adapter | Five public test clips, finite pages, unavailable/expiry fixtures, no Canvas/Atlas dependency. Native playback/paging observed. | Physical-phone playback acceptance. |
| 8. Exact setup/env/handoff | Mobile README/.env.example; owned API READMEs, server env placeholders and isolated dependency lock. | Deployment HTTPS API origin and scoped Atlas runtime credential. |

Adi's identity/entertainment repositories, validators, indexes and backfill drafts
are implemented and tested against a real local MongoDB 8.0.38 server. Hosted
Atlas now also passes connection, commit/rollback and shared constraint checks.
The published core/video migrations from Agastya's source snapshot
36fbc201 are applied; his runtime/migration source and Amogh's academic code were
not edited. Agastya still integrates real owner adapters/routes and runtime
dependencies; Amogh still owns academic persistence. A scoped runtime credential,
API hosting and physical-device acceptance remain open.

Demo scope decision, November 14: the user accepts confirming an email and then
returning to the app to sign in manually after the localhost redirect error.
Redirect UX and custom SMTP are explicitly deferred. Use existing confirmed demo
accounts for reliable demo access; broader signup/email-delivery acceptance is
deferred. Keep the current email-confirmation setting enabled. These deferrals
do not block private Storage setup or authenticated app/API integration.

## Milestone A2 — provider acquisition experiment

User direction updated November 14, 2026: prioritize Instagram through instagrapi
because account-specific recommendations are required. Use the existing account
selected by the user for the first session test. TikTok-Api was researched but
not live-tested; the user deferred that experiment because its logged-out data
does not meet this requirement. Both are unofficial Python libraries, not
guaranteed working services. Keep providers behind the same adapter.

The [local Instagram probe](../../services/api/app/modules/entertainment/experiments/README.md)
has passed its first live retrieval: four unique Reels and four HTTPS playback
candidates on November 14, 2026. See [the measured results](../status/ADI.md#a2-instagram-experiment--live-retrieval-verified).
Test logged-in Reels discovery, not only user_clips (a creator's posted Reels).
The account owner confirmed the four Reels' topics/creators look familiar. This
is qualitative evidence of relevance; exact native-app ranking and continued
recommendation behavior remain unverified.

Live-feed follow-up, November 14: implemented an owner-bound server session,
on-demand provider paging, retry-stable app cursors, leftovers/deduplication,
known-asset playback re-resolution, and bounded rolling mobile prefetch. The
existing saved four-Reel adapter remains finite. See [live setup](../ADI_INSTAGRAM_LIVE.md).
Fifty-two synthetic live/setup backend tests and thirteen existing entertainment
tests pass; mobile tests cover 250 clips without exceeding the 100-record window.
The first connection attempt stopped in app sign-in; the operator-UUID option
then reached Instagram login, which requested phone approval/verification.
The helper now reports safe stage-specific errors and preserves device identity
across manual attempts, including its device-registration key. Local code input
now waits for a supported 2FA challenge and SMS method selection; session
publication requires a successful current-user read. Safe request-phase/status
diagnostics distinguish remaining client rejections without raw provider data.
A user-run attempt exposed a CAA/legacy password loop. The optional local
--browser-session mode restores the owner's official-browser session and verifies
its identity without an SDK password request. The user-run connection verified
two live pages containing four unique Reels and a continuation cursor. Useful
continued acquisition beyond four and physical-phone playback remain unverified.
Actual later-page retrieval/renewal and physical-phone
acceptance remain unverified. The user approved the authenticated Expo tunnel
transfer for this phone test. Shared core assembly remains Agastya's work; no
academic or shared database code was changed.

Separate discovery from playback validation:

1. Retrieve a small list of real clips and metadata. **Verified:** four Reels
   retrieved through the existing account's authenticated discovery session;
   creator, caption, duration, source URL and candidate video URL fields checked.
2. Normalize them into EntertainmentVideo objects. **Verified for the saved
   batch:** four records pass the shared v1 schema and feed the local iOS preview.
3. Verify a playable source for each clip on the actual iPhone.
4. Test expired/unavailable resources and pagination. **Synthetic/local-cache checks pass:** scoped signed cursors, stale batches, expiry, unavailable records, provider cursor traversal/end/repeat handling. Live second-page acquisition and provider URL renewal remain unverified; the probe now supports explicit --pages 2 (maximum 3).
5. Record provider, timestamp, session requirements and results in your status file.

Simulator preview: `npm run ios:instagram`, then Explore the demo → Your feed.
Instagram playback was observed in the iPhone 17 simulator, including the fourth
clip with accumulated watch time. All four CDN URLs returned HTTP 206 video/mp4
without provider cookies. Physical-iPhone verification remains open; do not mark
item 3 complete from simulator/HTTP checks. The saved batch has no live pagination.

TikTok-Api documents trending.videos; instagrapi documents user_clips, feed helpers,
and clip downloads. Do not claim access to a personal FYP from a trending response.
instagrapi's explore_reels/reels methods target clips/discover and clips/connected;
discovery retrieval is now live-tested, with account-owner confirmation of familiar
topics/creators. Connected-feed retrieval, exact native-app ranking and ongoing
personalization updates remain unverified.
Provider login/cookies remain on the backend. Prefer a demo account if credentials
are required. Never embed social account passwords or cookies in the mobile app.

Fallback ladder: working adapter → previously prepared playable catalog → curated
TikTok embeds → explicit synthetic/local demo assets. Distinguish modes in your
handoff; do not pass fixtures off as live retrieval.

## Milestone A3 — intuitive phone scrolling

- Full-height portrait video cards and reliable vertical paging.
- Exactly one audible/playing card at a time.
- Pause when backgrounded or navigating away.
- Loading placeholders, retry, unavailable-video skip, and empty feed recovery.
- Respect iPhone safe areas; captions remain readable above controls.
- Preload a small upcoming buffer rather than every video.
- Display creator attribution/source where available.
- Keep watch/skip events separate and include actual visible playback duration.

For the first deliverable, call GET /v1/entertainment/feed. Later switch the
feed source to GET /v1/feed without rewriting the player.
Feed ordering belongs to Agastya's API, not a second mobile recommender.

Acceptance: demonstrate signup/login and a sustained scroll through playable
entertainment on a physical iPhone, including one background/resume and one
unavailable item. Record what was actually tested.

### A3 implementation cross-reference — November 14, 2026

| A3 bullet | Current implementation/evidence |
|---|---|
| Full-height cards/vertical paging | FlatList paging and safe-area controls; simulator traversed the five-card fixture feed with the accessible next/skip controls and loaded its second page. Physical gesture acceptance remains open. |
| Exactly one playing card | BufferedPlayerController pauses the standby before granting active playback; two bounded native buffers, one VideoView. Fake-driver exclusivity/race tests pass. |
| Pause in background/away | Foreground/focus/visibility/manual gates; simulator watch total retained 39s through background/resume and stopped in The lab. Physical audio exclusivity remains open. |
| Loading/retry/skip/empty recovery | Native failed-item Skip recovered; load and post-load stall watchdogs, URL resolution on expiry, stale-page reload and cancellable requests. Real renewed Instagram URLs remain untested. |
| Safe areas/captions | Native layout inspected; three-line captions above tabs, accessible paging alternative. |
| Small preload buffer | One paused upcoming native player, preferred five-second forward buffer; promotion/reuse tested. Rolling metadata window capped at 100 records, with foreground near-end paging and eviction only behind the selected clip. |
| Attribution/source | Creator display/handle and original-source link. |
| Separate actual watch/skip events | Media-position deltas, wall bounds and loop accounting exclude stalls/seeks/background. Normal paging emits a distinct skip; local diagnostics only. A4 owns server event delivery. |

A3 remains **not accepted** until the physical-iPhone signup/login + sustained
scroll + background/resume + unavailable-item scenario is observed. Simulator,
unit and HTTP checks do not substitute for that acceptance.

## Milestone A4 — integrate learning when ready

- Wire Amogh's academic feature exports into a separate course/settings flow.
- Render the shared discriminated feed union: entertainment, study, quiz.
- Wire Agastya's quiz component and disable scrolling while pending.
- On a successful answer, unlock even when incorrect and show explanation.
- Discard unseen prefetched items after recommendation_revision changes.
- Send playback/session events with unique event IDs.
- Show study-course context without exposing provider or renderer implementation.

## Handoffs

To Amogh: current-user identity shape, authenticated request helper, navigation
entry points, app theme primitives, package import convention.

To Agastya: normalized entertainment catalog/adapter, player source capabilities,
real device playback results, event producer, and API authentication adapter.

Ask for dependency changes with the required package/version/purpose rather than
editing the shared Python manifest. Adi owns root JS lockfile integration.

## Meaningful checks

Auth/session behavior, normalized provider responses, deduplication, cursor
handling, expired media, no double playback, server rejection of forged identity.
Use synthetic fixtures in tests and keep all credentials/raw media out of git.

## Out of scope for your first milestone

Canvas, model generation, training recommendation models, native TikTok
modification, Screen Time, social posting, payments and a polished settings suite.
Complete the simple phone feed before expanding.
