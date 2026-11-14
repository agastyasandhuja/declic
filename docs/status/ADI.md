# Adi status

Updated November 14, 2026. The fixture-first Expo prototype runs in the iPhone 17
simulator. Native video playback, pause/resume, background/resume, navigation and
unavailable-clip skip recovery were observed. Supabase authentication is wired;
successful real-account signup/login and persisted-session restoration are still
unverified. Atlas and backend persistence are deferred at the user's request.

Implementation branch: `codex/adi-mobile-prototype`, based on the existing main
checkout. The earlier Atlas architecture decision was committed/pushed on main
as `d864185`. Existing environment/status work was preserved when branching.
The implemented app, fixtures, schemas, tests and setup guide are committed as
`aae5dca` (`feat(mobile): add fixture-first Expo prototype and auth shell`).

## Delivered

- Read root/nested instructions, Adi's task guide, project/integration documents,
  and identity, entertainment, academics, learning and feed contracts.
- Root npm workspace and lockfile, Node 24 declaration, Expo SDK 58 + React Native
  + TypeScript app in apps/mobile. No other owner's implementation was edited.
- Email signup/login UI, confirmation messaging, logout, session restoration,
  foreground token refresh, and one app-wide Supabase session provider.
- Native session adapter backed by Expo SecureStore: Unicode-safe chunks,
  serialized access and manifest commit after successful chunk writes. Passwords
  are not persisted. Web preview uses per-tab sessionStorage.
- Full-height paged fixture feed with one shared expo-video player, serialized
  source changes, foreground/focus/manual-pause gates, mute, loading/error states,
  retry/skip and bounded pagination. Visible watch observations remain local.
- Development-only synthetic demo entry, synthetic course cards, and academics /
  learning component slots in The lab. These are placeholders for teammate work,
  not Canvas ingestion, generated lessons, quiz grading or a unified feed.
- Authenticated API client, bearer token attachment, HTTPS origin/path checks,
  timeout/cancellation, one refresh/replay after 401, structured errors and
  idempotency protection for mutation replay. No mobile Atlas connection.
- Owned versioned JSON Schemas, generated TypeScript wire types, runtime Ajv
  validation, synthetic identity/catalog and edge-case fixtures. Unknown optional
  fields are tolerated; server-only playback headers_ref is rejected.
- Exact setup, environment placeholders, test commands and teammate integration
  instructions in apps/mobile/README.md. Actual public Supabase configuration
  stays in ignored apps/mobile/.env. No credentials or video files were added.

## Exported interfaces and fixtures

- `apps/mobile/src/integration/index.ts`: FeatureScreenProps, ApiClient,
  RequestOptions, ApiError, CurrentUser, EntertainmentVideo, PlaybackSource,
  Button, theme and useAuth. Props are user, api, theme, isPreview, onBack and
  onOpenFeed. Adi owns registration in src/integration/registry.ts and navigation.
- `src/features/feed/source.ts`: FeedSource, createFixtureSource,
  createApiFeedSource and eligibleVideos. Live routes match the entertainment
  contract; they have not been tested against a running FastAPI backend.
- `src/lib/playback/SinglePlayerController.ts`: serialized source replacement
  and playback gates. Only the active card renders the one VideoView.
- `src/features/feed/FeedScreen.tsx`: LocalPlaybackEvent with video_id,
  event_type, position_ms and actual visible_watch_ms. This is local diagnostics,
  not the final unified-feed event envelope or server delivery implementation.
- `contracts/schemas/identity/current-user.v1.schema.json` describes the internal
  CurrentUser; `entertainment/feed-page.v1.schema.json` describes the v1 feed,
  EntertainmentVideo and client PlaybackSource. Markdown field names are intact.
- `fixtures/identity/current-user.json`: synthetic learner. Entertainment feed:
  five public test-media URLs, provider/acquisition_mode fixture, unknown durations.
  Edge-case catalog adds duplicate provider ID, unavailable and expired items.
  Deliberately broken first-clip mode is available in The lab.

## Commands actually run and results

- Workstation setup: Homebrew node@24 installed; fresh shells report Node
  v24.22.3 and npm/npx 11.19.1. npm registry ping passed. macOS is 26.7.3.
- `xcode-select -p`, `xcodebuild -version`, `xcodebuild -checkFirstLaunchStatus`:
  passed after the user completed Xcode setup; Xcode 27.2 is selected.
- `xcodebuild -downloadPlatform iOS`: installed iOS 27.2 simulator runtime.
  `xcrun simctl boot` / `bootstatus`: iPhone 17 booted. Expo installed matching
  simulator Expo Go and the native Metro bundle succeeded.
- Expo browser authorization finished with user-approved personal Viewer and
  hackumass-14 organization Developer access. Fresh
  `npx --yes expo@latest whoami`: ritzditz, exit 0. This app has no EAS project ID
  linked yet; Expo Go development does not require one.
- Supabase public Auth settings check: HTTP 200 with supplied public config,
  email enabled, signup allowed and email confirmation required. Missing key and
  current-user request without a session returned 401. These are endpoint checks,
  not completed account authentication.
- Official blank TypeScript SDK 58 template generated in a temporary directory;
  app files copied without overwriting existing .env or instructions. The initial
  explicitly versioned create-expo-app request returned ETARGET; @latest succeeded.
- `npm install`, Expo dependency installation and web dependency installation:
  passed; package-lock.json records versions. No automatic audit fix was applied.
- `npm run typecheck`: passed (strict TypeScript).
- `npm test`: 14/14 passed. Covers secure storage across adapter recreation and
  torn writes, source races, background/focus gates, error recovery, authenticated
  API refresh, safe mutation retries, timeout and fixture validation/pagination.
  These use fake storage/player/API drivers; they do not verify live providers.
- `npm run contracts:generate` and `npm run contracts:check`: passed; generated
  types match the owned JSON Schemas.
- `npx expo-doctor@latest`: 20/20 checks passed.
- `npx expo export --platform ios --output-dir /private/tmp/hackumass-mobile-ios`:
  passed; native Hermes bundle and assets exported outside the repository.
- HTTPS one-byte range checks for all five fixture URLs: HTTP 206, video/mp4.
  The original gtv sample host returned 403 and was replaced with reachable
  ExoPlayer/AndroidX test-media URLs. No media bytes were saved to the repo.
- Browser QA: empty-email validation, demo entry and navigation observed; one
  video element reported readyState 4 with no error. Explicit full-container
  video dimensions fixed the browser's intrinsic-height layout issue.
- Native iPhone 17 simulator: observed Big Buck Bunny, the short interlude and
  color-in-motion playback; pause/play, Courses and the academics slot worked.
  Deliberate missing clip displayed recovery UI; Skip advanced to the next clip,
  where visible watch activity accumulated. The failure toggle was turned off.
- Native background/resume: Home displayed the simulator home screen; after more
  than a minute away, the counter resumed from 22s to 23s rather than adding the
  background interval. The working app was left open. A stale loading indicator
  over playing video was corrected. Physical iPhone playback is not yet verified.
- `npm audit --omit=dev`: three moderate transitive findings through
  @expo/fingerprint / minimatch (GHSA-g3hv-75wg-m249), no high/critical findings.
  npm's suggested Expo downgrade was not applied. Recheck upstream updates before
  release; the current Expo version passes doctor and bundles successfully.
- Final typecheck, 14-test suite, generated-schema check, iOS export and
  `git diff --check` passed after the final UI/schema fixes. Staged credential
  scan passed; git confirms the actual .env is ignored and untracked.

## Teammate handoff and remaining setup

1. Everyone can run the demo without Atlas, FastAPI, Canvas or generation keys:
   Node 24, npm ci, configure .env from the example, npm start, Explore the demo.
   Xcode/iOS runtime are installed on this workstation. Metro remains on port 8081;
   use its i/w shortcuts, or restart with npm run ios. Physical phones need an
   SDK-compatible Expo Go app and network access to the laptop's Metro address.
2. Amogh / Agastya: export a React Native component accepting FeatureScreenProps
   from your owned mobile package. Use a domain fake adapter when isPreview is
   true; the shared API intentionally provides no credentials in demo mode. Send
   the component export and package/dependency requirements for Adi to register.
   Add no separate navigation root or auth store. No messages have been sent.
3. Real Auth acceptance still needs a controlled account: signup, email delivery /
   confirmation, invalid credentials, login, app restart with session retained,
   logout/private-state clearing, and network-loss recovery. Storage behavior is
   unit-tested; an actual authenticated SecureStore session is not yet observed.
4. Agastya's backend handoff: core token verification / get_current_user and
   authenticated GET /v1/me, plus assembly of the entertainment routes. Missing /
   invalid token rejection and cross-user ownership require backend integration
   tests. This mobile prototype does not implement a fake accepting server.
5. Set EXPO_PUBLIC_API_BASE_URL to the reachable HTTPS API origin, restart Metro,
   sign in and use The lab's connected-feed switch/API check. Backend transport,
   live entertainment retrieval and expiring signed URL refresh remain untested.
6. Unified feed ordering, feed-session event delivery, study/quiz cards and quiz
   gating await Agastya's exports/contracts; actual academic data awaits Amogh's
   exports. The prototype exposes integration slots so their UI work can proceed.
7. Atlas cluster/URI, collection validators/indexes, application profiles/jobs,
   object-storage policies and renderer isolation remain later backend work.
   Shared Atlas setup/ordered database assembly stays with Agastya, academic
   persistence with Amogh, and Adi domain drafts with Adi. No Atlas connection is
   configured or tested. Supabase Auth/Storage responsibilities are unchanged.
8. Physical-iPhone sustained swipe, audio exclusivity and unavailable-item recovery
   remain acceptance checks. Android, production build signing/TestFlight, EAS
   cloud linkage and a production portrait-media catalog are not yet verified.
   Media preloading is not implemented; the prototype loads one source at a time.
