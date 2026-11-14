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

## A1 acceptance audit

Cross-checked the implementation against all eight numbered requirements in
[Milestone A1](../tasks/ADI.md#milestone-a1--app-and-identity). The task guide now
links each requirement to its implementation and evidence. **A1 remains in
progress:** implementation coverage is not acceptance, and the fixture demo does
not establish successful real authentication.

| A1 acceptance criterion | Actual result | Work needed to accept |
|---|---|---|
| New account and returning-user login | Implemented, not validated end to end. Public Supabase settings respond and require email confirmation. | Create a controlled account, confirm its email, sign out and sign back in using the app. |
| Invalid credentials and network loss give usable messages | Message branches exist; empty-email UI validation observed. Fake API timeout test passed. Live Auth rejection/network-loss behavior not tested. | Exercise a rejected login and an offline request, then reconnect and retry successfully. |
| Restart retains a valid session; logout clears private state | SDK persistence/restoration and native SecureStore adapter implemented. Fake-store recreation/removal tests passed; actual authenticated restart/logout not observed. | Sign in, terminate/relaunch the app, confirm the same account is restored, sign out, and relaunch to verify authentication is required and private shell state is cleared. |
| Feed accessible without Canvas | Passed for the development fixture demo in the iPhone simulator. No Canvas, Atlas or FastAPI dependency. | Recheck the same feed after real sign-in and on the physical iPhone; those paths remain unverified. |
| API rejects missing/invalid tokens and caller-selected identity | Not implemented/validated by this prototype. Client token handling is unit-tested, but services/api/app/modules/auth is still a scaffold. | Adi implements verify_access_token; Agastya integrates get_current_user and router assembly. Test missing, invalid, expired and forged tokens plus cross-user access against protected routes. |

The remaining A1 Auth and authorization work is still required. The user has now
selected a limited A2 Instagram experiment in parallel; serving private provider
feeds to app users must wait for protected API authentication. The prototype also
contains part of A3 playback and A4 integration slots; those additions do not
complete A1 acceptance. Atlas profile/catalog persistence remains deferred.
Token verification and basic Auth acceptance can proceed independently of Atlas.

Audit verification: reread the current implementations and test coverage, and
reran root `npm run typecheck`, `npm test` and `npm run contracts:check`:
all passed, including 14/14 tests. No new live Auth or device test is implied
by this audit.

## A2 Instagram experiment — live retrieval verified

**A2 item 1 is complete for the first experiment.** The user ran the probe locally
with their existing account. The sanitized report confirms authenticated discovery
retrieval of four unique Reels with four HTTPS video candidates. The account owner
confirmed familiar topics/creators. Normalization and local iOS simulator playback
are now verified as recorded below. Physical-iPhone playback, pagination, exact
feed parity and ongoing personalization updates remain pending checks.

### Live evidence — November 14, 2026

- First attempt: November 14, 2026, 07:49:28–07:50:33 UTC. Report showed
  ClientNeedsUpgradeError, authenticated=false and zero retrieved clips. The user
  identified an incorrect password. The error class alone did not establish an
  outdated app, a challenge or valid credentials; upstream [issue 2807](https://github.com/subzeroid/instagrapi/issues/2807)
  documents that ambiguity.
- Local inspection confirmed instagrapi 3.2.12 and its default Android app profile
  449.0.0.52.84 with its matching Bloks configuration. No package/profile/code
  change or automated login retry was made between the two attempts.
- Second attempt, after the user's credential correction: November 14, 2026,
  07:54:21–07:54:47 UTC. The user ran the same probe in their own Terminal.
  report.json: stage=retrieved, authenticated=true, surface=discover, requested=5,
  retrieved=4, https_candidates=4. The request asks for up to five; four is a
  successful partial page, not evidence of pagination or a five-item guarantee.
- Checked the local catalog without printing its private contents: four unique
  IDs; all records have creator handles, caption strings, nonnegative numeric
  durations, Instagram HTTPS source URLs and HTTPS candidate playback URLs.
  report.json and catalog.json are mode 0600 and remain ignored by Git.
- After retrieval, the account owner confirmed that the four Reels' topics or
  creators look familiar compared with their usual Instagram recommendations.
  This is qualitative relevance evidence from the selected account, not a test
  of exact native-app ranking, cross-account differences or ongoing adaptation.
  The probe's automatic personalization_verified/native_playback_verified flags
  remain false; it cannot perform this human comparison itself. The probe report
  predates the separate simulator playback test below; actual iPhone remains untested.
- Commands for this verification: a local Python JSON/metadata validation with
  aggregate-only output; git status; read-only inspection of installed SDK
  version/profile and login handling. No credentials, provider responses, clip
  IDs, creator names, recommendation content or signed media URLs were committed.

### Preparation and boundaries

- User requires account-specific entertainment and chose Instagram with their
  existing account's history. TikTok-Api was researched, not live-tested; its
  public-data approach was deferred. This is an explicit user-directed change
  from the initial TikTok-first experiment order, not a failed TikTok test.
- Reviewed current primary sources: [instagrapi Reels readers](https://github.com/subzeroid/instagrapi/blob/master/instagrapi/mixins/timeline.py),
  [login/session documentation](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/interactions.md),
  [login migration](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/login-migration.md),
  and [Meta's Instagram Platform](https://developers.facebook.com/documentation/instagram-platform).
  Source exposes clips/discover and clips/connected under an account session.
  This is not proof of the same personalized stream/ranking as Instagram's app.
- Added [a standalone probe and run guide](../../services/api/app/modules/entertainment/experiments/README.md)
  within Adi's entertainment module. One SDK login call, then a single small Reels
  page; up to five unique clips, with captions/creator/duration/URL candidates.
  No mobile source switch, API route, Atlas work or shared Python manifest change.
- Credential entry uses hidden local terminal prompts. No password/cookie/session
  file is saved. Provider logs/raw exceptions are suppressed; account verification
  errors stop without automatic checkpoint resolution. Normal login may include
  the SDK's CAA fallback. Explicit likes/follows/posts/messages/seen-state calls and
  media downloads are absent; normal login/feed requests can affect provider state.
- Local catalog data remains under ignored .local/instagram-probe with private
  permissions. A separate report contains stage/counts/error class, without raw
  payloads, account identifiers or session credentials. Actual data is not a fixture.
- Commands run: `python3 -m venv .local/instagram-probe/venv`; isolated
  `python -m pip install instagrapi==3.2.12` from PyPI succeeded. Version verified
  from PyPI metadata; `python -m pip check` passed. This isolated install is not
  Agastya's shared service dependency manifest; integration dependency request is
  instagrapi 3.2.12 for a later accepted adapter, pending live results.
- Probe `--help` passed. `python -m unittest discover -s
  services/api/app/modules/entertainment/experiments -p 'test_*.py' -v`: 3/3 passed.
  Tests cover Reels filtering/deduplication, private output permissions/location,
  and withholding simulated credentials/provider errors from reports and stdout.
  `git check-ignore` confirms both output files are ignored. No live provider
  request was made by these tests.
- Computer-use access to Terminal was rejected by the tool's safety restriction.
  No alternative control path was attempted. The user must run the documented
  command in their own Terminal to enter credentials privately.
- A2 item 1 (real clips/metadata): verified by the second live attempt above.
  Item 2 (normalized EntertainmentVideo): now verified for the saved batch by the
  mobile integration below. Item 3 (actual iPhone playback), item 4 (expiry/outage/pagination), exact
  feed parity and ongoing personalization updates remain untested. Item 5 now
  includes the first failure, successful retrieval and account-owner relevance
  comparison; append later results here.

### Saved-batch simulator integration — November 14, 2026

- Branch codex/adi-instagram-preview builds on the existing probe/prototype.
  Added a Node/TypeScript normalizer, prepare command and saved_instagram feed
  adapter. Four private records pass the existing EntertainmentFeedPage v1 schema.
  IDs are namespaced for this preview, metadata stays cached, ordering is preserved,
  duplicates are removed and no cookies/headers/provider credentials are copied.
- Normalized data goes to ignored .local/instagram-probe/feed.v1.json (mode 0600).
  Metro resolves that file only for an explicitly enabled development iOS bundle;
  normal runs, web/Android and production resolve an empty tracked catalog.
  No contract fields, other owners' implementations, shared Python dependencies,
  API route, cloud service or Atlas database were changed.
- `npm run ios:instagram`: passed; normalizer prepared four records, Expo started
  with --localhost and --ios, and the native bundle succeeded (963 modules).
  `lsof -nP -iTCP:8081 -sTCP:LISTEN` confirmed 127.0.0.1:8081 only. Middleware also
  rejects non-loopback requests. No LAN/tunnel is used for the personal preview.
- Read-only one-byte range checks of all four candidate media URLs: HTTP 206,
  video/mp4, Content-Range present, without Instagram cookies. No media bytes were
  saved to the repository. This checks URL reachability, not every clip's device
  playback or a supported expiry/refresh flow.
- Opened Explore the demo in the iPhone 17 / iOS 27.2 simulator. Observed Instagram
  media rendering in the shared native player; the fourth clip showed 4/4 and 9s
  watched, and later local activity showed 12s visible. The lab displayed the saved
  Instagram switch enabled. The user was also interacting with the simulator;
  automation did not overwrite their navigation. No claim that each clip or
  physical-iPhone sustained playback was independently verified.
- The header says SAVED REELS; The lab can return to synthetic samples. Captions
  are limited to three visible lines. This is a finite saved batch: no background
  Instagram login, live pagination, automatic URL renewal or watch feedback.
  The auth identity in development demo remains synthetic; this is a local
  user-authorized playback test, not a server-backed private feed or A1 sign-off.
- `npm run typecheck`, `npm test` (18/18), `npm run contracts:check`: passed.
  New tests cover normalization/credential exclusion, hostile URLs/invalid dates,
  finite-batch behavior and private-catalog platform/development gates.
- `HACKUMASS_INSTAGRAM_PREVIEW=1 npx expo export --platform ios --output-dir
  /private/tmp/hackumass-instagram-release`: passed. Scanned release artifacts for
  the actual private provider IDs, creator handles and playback URLs: no matches.
  Scanned tracked/reviewable untracked files for those values: no matches.
  `git check-ignore` confirms the normalized feed stays excluded.
- Remaining: actual iPhone playback, live provider refresh/pagination, signed-link
  expiry recovery and the three A1 auth/authorization acceptance gaps. Keep the
  protected API/ownership work ahead of any remotely served per-user provider feed.

## Delivered

### Physical-phone connection preparation — November 14, 2026

- Started a separate ordinary Expo Go server with
  `HACKUMASS_INSTAGRAM_PREVIEW=0 npx expo start --go --lan --port 8082`.
  The private Instagram simulator server remains on localhost:8081. This phone
  preview contains public fixture clips, not the saved personal Instagram batch.
- User confirmed connecting the Mac to their iPhone hotspot. Refreshed Expo after
  the address change and generated a local QR PNG using Expo CLI's installed
  QR encoder. No hotspot password or provider/session credential was requested.
- `npx expo whoami` returned ritzditz. Local phone-server checks returned HTTP 200
  for the Expo manifest (SDK 58.0.0) and its iOS development bundle. Scanned that
  bundle for the actual Instagram IDs, creator handles and media URLs: no matches.
- Xcode device discovery showed the simulator only, which does not prevent Expo
  Go network use. Metro's phone-server debug target list was empty when checked.
  The user reported that the hotspot LAN connection stalled/could not connect.
- Stopped the phone's LAN server and started
  `HACKUMASS_INSTAGRAM_PREVIEW=0 npx expo start --go --tunnel --port 8082`.
  Expo supplied an HTTPS on.expo.app tunnel without an additional installation.
  Verified its iOS manifest externally: HTTP 200, SDK 58.0.0, launch asset present.
  Generated and displayed a replacement QR for that active tunnel. The private
  simulator server was not tunneled or changed. Phone launch/playback confirmation
  remains pending; do not infer it from the server/QR being ready. The three A1
  acceptance gaps remain open.

### Mobile prototype implementation

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
4. Backend auth remains shared work: Adi owns the auth module's
   verify_access_token adapter and identity route implementation; Agastya owns
   core get_current_user and router assembly. These are still scaffolded. Missing /
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
