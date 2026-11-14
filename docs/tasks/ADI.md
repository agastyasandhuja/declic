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
4. Implement proposed Supabase Auth signup/login/logout and persistence using
   current provider guidance. Show email confirmation when required.
5. Keep session credentials in secure device storage; never store passwords.
6. Define one API client that attaches app access tokens and handles expired sessions.
7. Add a fixture entertainment adapter so player work proceeds independently.
8. Document exact install/start/device-test commands and public environment names.

Acceptance:

- New account can be created and a returning user can log in.
- Invalid credentials and network loss produce usable messages.
- Restart preserves a valid session; logout clears local private state.
- Feed is accessible without Canvas.
- API rejects missing/invalid app tokens; caller cannot choose another user ID.

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
