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

A1 is **in progress, not accepted**. All eight mobile implementation items have
code or documentation, but live authentication and backend enforcement have not
passed acceptance. "Implemented" below describes code present, not a successful
real-account test. See [A1 acceptance evidence and remaining work](../status/ADI.md#a1-acceptance-audit)
for the separate acceptance checklist.

| A1 item | Implementation | Evidence and remaining verification |
|---|---|---|
| 1. Expo + React Native + TypeScript in apps/mobile | [Mobile manifest](../../apps/mobile/package.json), [entry point](../../apps/mobile/index.ts), [TypeScript config](../../apps/mobile/tsconfig.json) | Typecheck, Expo Doctor 20/20 and iOS export passed; app launched in the iPhone 17 simulator. |
| 2. Repository root remains a workspace | [Root manifest](../../package.json), [lockfile](../../package-lock.json) | Root commands target the mobile workspace; install, typecheck and tests passed. |
| 3. Auth/feed navigation and loading/error states | [App shell](../../apps/mobile/src/AppShell.tsx), [auth screen](../../apps/mobile/src/features/auth/AuthScreen.tsx), [feed screen](../../apps/mobile/src/features/feed/FeedScreen.tsx) | Demo navigation, empty-email validation and unavailable-clip recovery observed. Real auth/network failure paths remain unverified. |
| 4. Supabase signup/login/logout and persistence | [Supabase client](../../apps/mobile/src/lib/auth/supabase.ts), [auth screen](../../apps/mobile/src/features/auth/AuthScreen.tsx), [session provider](../../apps/mobile/src/state/AuthProvider.tsx) | SDK calls, email-confirmation messaging, restoration and refresh implemented. Successful account creation, confirmation, login, restart and logout still need a controlled account. |
| 5. Secure session storage; no password persistence | [Native SecureStore adapter](../../apps/mobile/src/lib/auth/sessionStorage.native.ts), [chunked storage](../../apps/mobile/src/lib/auth/chunkedStorage.ts), [storage tests](../../apps/mobile/tests/storage.test.ts) | Fake-store tests passed for adapter recreation, Unicode, interrupted writes and removal. Actual authenticated device storage/restart/logout remains unverified. Web uses per-tab sessionStorage. |
| 6. One authenticated API client and expired-session handling | [API client](../../apps/mobile/src/lib/api/client.ts), [session binding](../../apps/mobile/src/state/AuthProvider.tsx), [API tests](../../apps/mobile/tests/api.test.ts) | Fake-API tests passed for bearer attachment, refresh, expiry, timeouts and safe replay. Live backend integration and server token/ownership enforcement remain pending. |
| 7. Independent fixture entertainment adapter | [Feed adapters](../../apps/mobile/src/features/feed/source.ts), [catalog](../../fixtures/entertainment/feed.json), [fixture tests](../../apps/mobile/tests/fixtures.test.ts) | Fixture validation/pagination tests passed; all five media URLs returned HTTP 206. Playback observed in the simulator without Canvas, Atlas or FastAPI. |
| 8. Exact setup/device commands and public env names | [Mobile setup guide](../../apps/mobile/README.md), [environment example](../../apps/mobile/.env.example) | Install/start/simulator/phone instructions and placeholders present. Actual .env stays ignored; physical-phone procedure is documented but not yet validated. |

Next A1 work: validate real Auth on the simulator/device, then implement Adi's
server auth adapter and coordinate Agastya's core dependency/route assembly to
test protected endpoints. These checks do not require Atlas application-data
persistence. The user's current database deferral does not mark them complete.

## Milestone A2 — provider acquisition experiment

Test TikTok-Api first, instagrapi as an alternative. Both are unofficial Python
libraries, not guaranteed working services. Keep them behind the same adapter.
The initial feed may be nonpersonalized.

Separate discovery from playback validation:

1. Retrieve a small list of real clips and metadata.
2. Normalize them into EntertainmentVideo objects.
3. Verify a playable source for each clip on the actual iPhone.
4. Test expired/unavailable resources and pagination.
5. Record provider, timestamp, session requirements and results in your status file.

TikTok-Api documents trending.videos; instagrapi documents user_clips, feed helpers,
and clip downloads. Do not claim access to a personal FYP from a trending response.
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
