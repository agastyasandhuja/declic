# Mobile prototype

Expo SDK 58 + React Native + TypeScript. Adi owns this app and the root npm
workspace. Owned Atlas-compatible repositories and database drafts are ready for backend
assembly; no Atlas cloud connection is configured. Supabase Auth is wired independently;
the fixture feed and development demo need no backend.

## Install and run

Use Node 24 LTS (see root .nvmrc). Run from the repository root:

```sh
npm ci
cp apps/mobile/.env.example apps/mobile/.env
npm start
```

Preserve an existing .env instead of copying over it. Add the Supabase project URL
and publishable key to that ignored file for real signup/login. Never add server
keys, Canvas tokens or an Atlas URI to mobile configuration. Restart Metro after
changing environment variables.

- Physical iPhone: install Expo Go supporting SDK 58; sign into the same Expo
  account in Expo Go and the CLI (`npx expo login --browser` from apps/mobile).
  Keep laptop/phone on the same reachable network, then scan Metro's QR code.
- iOS Simulator: finish Xcode setup and install an iOS runtime in Xcode settings,
  then run `npm run ios`. Expo installs the matching simulator Expo Go app.
- Browser preview: `npm run web`. This is useful for UI checks; native playback
  and secure storage still require device/simulator checks.

If Metro is already running, use its `i`/`w` keys rather than starting another
server. To clear stale bundles, run `npx expo start --clear` from apps/mobile.
Shared fixtures and schemas are included in Metro's watch folders.

## Try the prototype

### Physical iPhone connection

The ordinary phone preview uses public fixture clips. It can run alongside the
private simulator preview on another port. From apps/mobile:

```sh
HACKUMASS_INSTAGRAM_PREVIEW=0 npx expo start --go --lan --port 8082
```

Connect the Mac and phone to the same reachable Wi-Fi, or enable Personal Hotspot
on the phone and connect the Mac to it. After changing networks, restart this
server to get a QR code using the new Mac address. On the iPhone, sign in to Expo
Go with the same Expo account as the CLI, scan the QR using Camera, open Expo Go,
and allow local-network access if prompted. Choose Explore the demo → Your feed.
Keep the Expo server running while testing. An SDK mismatch requires a compatible
Expo Go version; record the actual error rather than assuming phone playback works.

If the phone cannot reach the Mac on Wi-Fi/hotspot, stop only the phone server
and use Expo's tunnel, then scan its replacement QR code:

```sh
HACKUMASS_INSTAGRAM_PREVIEW=0 npx expo start --go --tunnel --port 8082
```

The tunnel is for the public fixture preview. Its URL changes when the server
restarts; use the currently displayed QR. Both Expo Go and the CLI must use the
same Expo account. The tunnel requires an internet connection on both devices.

The saved Instagram mode remains localhost-only and is not included in this phone
bundle. Do not start it through a LAN or public tunnel. A private per-user feed on
the phone needs its own protected integration; this initial connection test does
not complete A1 authorization or validate Instagram playback on a physical device.

### Fixture walkthrough

1. Choose **Explore the demo** on the sign-in screen. This entry exists only in
   development (`__DEV__` plus EXPO_PUBLIC_ENABLE_PREVIEW, default true).
2. Swipe the full-height **Your feed** cards. Tap to pause; use the speaker control
   to mute. Only the active card plays. One paused upcoming native player preloads a small
   buffer. Backgrounding and leaving the feed pause both drivers.
3. Open **Courses** for clearly labeled synthetic course cards.
4. Open **The lab** for component integration slots and local playback activity.
   Enable **Unavailable clip test** to restart the demo at a deliberate missing
   asset; verify retry/skip, then turn the switch off to restore the working feed.
5. Choose **Leave demo** to return to authentication. Preview state is temporary;
   it has a synthetic identity and cannot authenticate any API request.

The media catalog is fixtures/entertainment/feed.json. These are public test-media
URLs, not TikTok/Instagram retrieval or generated lessons. Edge-case fixtures also
include a duplicate provider item, unavailable item, expired link, and unknown
durations. No downloaded media bytes belong in Git. Sample clips are not promised
to have production portrait framing or a 30–60 second lesson duration.

## Saved Instagram preview in the iOS Simulator

After running the local [Instagram probe](../../services/api/app/modules/entertainment/experiments/README.md),
stop any existing Metro server and run this from the repository root:

```sh
npm run ios:instagram
```

This normalizes the ignored catalog to .local/instagram-probe/feed.v1.json,
starts Expo on localhost and opens the iPhone simulator. Choose **Explore the
demo**, then **Your feed**. The header says **SAVED REELS**. In **The lab**, turn
**Use saved Instagram clips** off to return to synthetic sample clips.

This is the saved batch retrieved from your account, not continuous live retrieval.
It ends after that batch; it does not send watch feedback to Instagram. Expired
URLs require running the probe again and restarting the preview. No provider
login credentials enter the mobile app. IDs use instagram_<provider_video_id>
for this local preview; a production backend will own stable catalog identity.
Acquisition mode is cached, and unknown signed-URL expiry stays null.

This mode is deliberately limited to local development iOS bundles. Metro binds
to 127.0.0.1, rejects non-loopback requests, and refuses private-preview startup
without --localhost. Normal npm start, web/Android bundles and production exports
resolve an empty catalog. Actual recommendation metadata and playback URLs stay
in ignored private files; never commit those files or publish a development bundle
containing them. No additional API service or database is introduced.

The three A1 acceptance gaps remain open. Before exposing a private feed through
the backend or to other devices, complete app-token verification and server-side
ownership checks for each user's Instagram connection. This local simulator test
does not validate those controls or physical-iPhone playback.

## Real authentication

Signup, email-confirmation messaging, login, logout, session restoration and token
refresh use @supabase/supabase-js. Native sessions are chunked into secure device
storage, with a small manifest committed only after all chunks are written.
Browser preview sessions use sessionStorage, scoped to the current browser tab.
Passwords are never persisted. Sign-out unmounts the private app shell, clearing
its feed, route, diagnostic state and synthetic data.

The configured project's public Auth endpoint was checked separately and requires
email confirmation. Successful signup/email delivery/login and actual persisted
session restoration still need a controlled test account; do not infer those from
the implemented UI or public endpoint checks.

## Backend connection

Set EXPO_PUBLIC_API_BASE_URL to the reachable **HTTPS origin** of Agastya's API and
restart Metro. After real sign-in, enable **Use connected feed** in The lab. It
uses GET /v1/entertainment/feed and the per-video playback-refresh route from the
v1 entertainment contract. **Check authenticated API** calls GET /v1/me.

The shared client attaches only the current app access token, performs at most one
refresh/replay after a 401, accepts only /v1 paths on the configured origin, and
handles timeouts/errors. Mutations replay only with an Idempotency-Key. The actual
FastAPI auth enforcement is a backend handoff and is not implemented by this app.
There is no Atlas connection in the mobile app. Playback observations are local
diagnostics; feed-session event delivery awaits Agastya's unified-feed integration.

## Teammate integration

See src/integration/index.ts for FeatureScreenProps and reusable Button/theme/API
exports. src/integration/registry.ts has `academics` and `learning` screen slots,
reachable through The lab. Adi owns registering package imports and navigation.

Amogh and Agastya should export a React Native component accepting:

```ts
type FeatureScreenProps = {
  user: CurrentUser;
  api: ApiClient;
  theme: typeof theme;
  isPreview: boolean;
  onBack(): void;
  onOpenFeed(): void;
};
```

Use a type-only import of FeatureScreenProps from the app integration index until
a shared package is agreed. Inject their domain's local fake adapter when
isPreview is true; demo mode deliberately provides no backend credentials. Do
not add another auth store or navigation root. Never authorize requests using
the user_id prop: the backend derives identity from the bearer token.

Deliver the component/export name plus package dependencies to Adi. The owner can
create their package.json under packages/mobile-academics or mobile-learning;
Adi adds its workspace dependency and integrates the root lockfile. Do not modify
another stream's implementation to fill a slot. The initial slots are placeholders,
not completed academic/learning features or a simulated server quiz gate.

## Checks

From the repository root:

```sh
npm run typecheck
npm test
npm run contracts:check
```

From apps/mobile:

```sh
npx expo-doctor@latest
npx expo export --platform ios --output-dir /private/tmp/hackumass-mobile-ios
```

TypeScript wire types in src/contracts/generated.ts are generated from Adi's
versioned JSON Schemas under contracts/schemas. After editing a schema, run
`npm run contracts:generate` at the root and commit its generated types. Runtime
Ajv validation uses those same schemas for feed/playback data and fixtures.

Behavior tests cover rapid-swipe source races, background/focus gating, playback
failure recovery, secure-storage torn writes/Unicode, authenticated API refresh,
timeouts, safe mutation retries, and fixture normalization/pagination. Record actual
simulator and physical-device acceptance results in docs/status/ADI.md.


## A1–A3 reliability update — November 14, 2026

The feed uses at most two native players: one active VideoView/audio source, one
paused upcoming media buffer (preferred forward duration five seconds). Source
replacement is serialized per slot. Gates cover visibility, route focus, manual
pause and app foreground. Load and post-load-stall recovery has a 15-second
watchdog; a stuck native load can be recovered with Reload feed, which releases
both players. Retry re-resolves a URL when the selected source supports it.
Saved Instagram retries reuse the saved URL; they cannot renew an expired link.

Visible watch duration counts measured media movement bounded by wall time,
excluding stalls, seeks, long sampling gaps and background/hidden time. Regular
paging emits a separate skip observation. These remain local diagnostics; event
submission to Agastya's unified-feed/session API is A4 work. Creator/source links
are available. The arrow button provides an accessible alternative to swipe
paging. Only 100 metadata records are retained; native media preloading stays at
one upcoming clip. An exhausted batch offers an explicit reload.

The API helper times out response-body stalls, rejects normalized paths escaping
/v1, and keeps the session on transient refresh outages. An unreadable saved
session offers both Retry and an explicit Clear saved session action. Real device
restart/logout/offline acceptance still needs a controlled account. User-reported
signup/email/login succeeded, but its confirmation page used the project's
localhost redirect; return to the app to sign in after confirmation. Production
Auth site/deep-link allowlisting remains backend/project setup.

Teammates can start immediately with `npm ci`, `npm run ios` and Explore the demo.
FeatureScreenProps/API/theme/navigation ownership remain as documented above.
The new [identity setup](../../services/api/app/modules/auth/README.md) and
[entertainment setup](../../services/api/app/modules/entertainment/README.md) give
exact isolated API/database test commands and backend dependency requests.
Physical-iPhone Instagram setup remains paused; no private catalog is tunneled.

## Live Instagram feed — November 14, 2026

The user has requested live account-session retrieval. The new backend adapter
uses the same authenticated entertainment routes; the old saved four-Reel mode
remains an explicitly selected fallback. See [live setup](../../docs/ADI_INSTAGRAM_LIVE.md)
for the local hidden-login helper, backend startup and HTTPS API configuration.
Forwarding private data through a public tunnel remains subject to the earlier
specific approval; no public tunnel is enabled automatically by these changes.

From the root, instagram:connect binds a server-only Instagram session to the
Supabase account, instagram:api starts the local owned factory, and
instagram:mobile selects the API feed with the saved bundle preview disabled.
The app still requires a reachable HTTPS API origin and the matching app sign-in.
Demo mode never receives private feed credentials.

Near-end pagination now runs only while focused/foregrounded, with at most one
pending page request. A rolling 100-record window evicts only already-passed cards
and retains the selected asset/unseen cards, allowing sessions beyond 100 clips.
Empty/duplicate traversal is bounded and offers retry without dropping loaded
videos. Native player/audio gates remain unchanged. Pure synthetic tests cover a
250-clip session; actual account pagination and physical-phone acceptance still
need the local connection/device checks.
