# Live Instagram feed — Adi demo setup

The live adapter replaces a finite saved catalog with on-demand account-session
Reels pages. It uses the existing authenticated entertainment API and player.
It does not promise exact native Instagram ranking, and app viewing does not send
likes/follows or explicit Instagram seen-state updates. No media bytes are stored.

Implementation and synthetic checks are ready. A user-run browser-session
connection verified the account and retrieved two live pages with four unique
Reels and a continuation cursor. Useful later-page acquisition beyond four and
physical-phone playback remain separate required checks, recorded in
[Adi status](status/ADI.md). The previous four-Reel retrieval does not prove them.

## 1. Prepare the isolated environment

From the repository root on this Mac, use the existing .local/instagram-probe/venv.
For a new checkout only:

```bash
python3 -m venv .local/instagram-probe/venv
.local/instagram-probe/venv/bin/python -m pip install -r services/api/app/modules/auth/requirements-dev.lock
```

Keep the existing ignored apps/mobile/.env public Supabase URL and publishable
key. These must match the account used in the app. Alternatively configure server
SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY. The helper reads these two values only;
it never sources an env file. Placeholders are in the entertainment .env.example.
Shared dependency/lock edits remain Agastya's work; request optional runtime
instagrapi==3.2.12 and jsonschema==4.26.0 for this integration.

## 2. Connect once in your own Terminal

```bash
npm run instagram:connect
```

Prompts: app email/password, then Instagram username/password. There is no code
prompt before the login request. App sign-in goes to Supabase; Instagram credentials go to Instagram.
Passwords use hidden input and are not saved. The verified Supabase UUID binds
the Instagram connection to the same app account. An operator who has already
copied that UUID from The lab can skip local app sign-in:

```bash
npm run instagram:connect -- --owner-user-id YOUR_APP_USER_UUID
```

This operator-only option is not a client request parameter. No private feed is
automatically assigned to the first signed-in API caller.

### Existing signed-in Chrome session

For the observed CAA → legacy → CAA password loop, use the SDK's documented
existing-session option rather than repeating the rejected password flow:

```bash
npm run instagram:connect -- --owner-user-id YOUR_APP_USER_UUID --browser-session
```

In Chrome, sign in on Instagram's official site. Open Developer Tools
(Option+Command+I), then Application → Cookies → https://www.instagram.com.
Copy only the Value of sessionid, enter the matching Instagram username in your
own Terminal, and paste the cookie at its hidden prompt. Never put the value in
chat, a command argument, an EXPO_PUBLIC variable, source code or screenshots.
This is a credential. The flag itself takes no value. Passwords/2FA stay in the
official browser login, and this path refuses any SDK password request.

The SDK's login_by_sessionid must succeed, followed by a current-user read that
matches both the session identity and the entered username. Only then can the
owner-only ready session be saved. Browser sessions can still be rejected for
private/mobile API use; no compatibility or recommendation parity is guaranteed.
The same bounded two-page check and phone acceptance are required afterward.
See [SDK login methods](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/interactions.md).

If Instagram returns a supported account-2FA context, the helper continues that
same challenge without another password login. It uses the reported SMS or
authenticator method; when the response does not identify a method, choose sms
or totp locally. SMS method selection happens before the hidden code prompt.
Enter only a fresh six-digit code for this attempt. Enter cancels if no SMS
arrives. There is one code submission and no automatic resend/retry. Account
checkpoints/profile verification remain in the official Instagram app; a single
unexpected SMS does not establish that the account uses routine SMS 2FA.

The helper verifies the new session with Instagram's current-user endpoint before
saving session/device settings in .local/instagram-live/connection.json
(0600, parent 0700), then checks at most two provider pages. Session cookies are
credentials: never paste, commit, bundle or upload this file. The saved session is
restored on subsequent API starts; no automatic login occurs during scrolling.
The redacted report records only timestamps, counts, status and safe error codes.
It now records the failing stage (app_login, instagram_login, or reels) and a
safe HTTP status when applicable. It also records a fixed login request phase,
bounded phase list/count and two-factor/session-verification booleans. These are
labels such as caa_password, legacy_password or device_registration, never raw
URLs, payloads, phone numbers, challenge contexts or codes. App credential, email-confirmation, timeout,
configuration and rate-limit failures are distinct. Known Instagram login
exceptions map to fixed codes, including INSTAGRAM_CHECKPOINT_REQUIRED,
INSTAGRAM_TWO_FACTOR_REQUIRED and INSTAGRAM_CLIENT_REJECTED. Only allowlisted
exception class names can appear; raw provider messages never do.
Two requests alone do not prove useful continuation: verify that later pages add
unique clips beyond the first batch. A one-page response with no continuation is
an observed provider end, not successful ongoing pagination.

On a challenge or rejection, review Instagram on the phone and reconnect locally
when ready. Do not loop login attempts. Reconnect/replacement requires restarting
the API so it loads the new owner/session. Keep the old saved catalog untouched
as a separate, explicitly selected fallback.

Before the first Instagram network login, the helper saves an owner-only device
profile under .local/instagram-live/device-<opaque-hash>.json. Manual attempts
using the same app UUID and Instagram username reuse its device identifiers.
Profiles retain device/CSRF cookies and the SDK's device-registration signing key,
never authentication cookies, authorization data or passwords. That device key
is private credential material: keep the profile local with mode 0600, just like
the ready session. A profile cannot be used by the API as a ready account session.
Complete approval/verification in the official Instagram app yourself, then make
one manual retry. The helper never resolves checkpoints automatically. This
follows the SDK's [device/session reuse guidance](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/best-practices.md).

The local login wrapper bypasses the SDK's hidden timeout/incomplete-read retries,
bounds its request sequence to 40 calls, and stops repeated password submission
to the same login endpoint. The SDK may follow an explicit CAA-to-legacy server
instruction once; it cannot loop back through the same password endpoint. No
mobile or public API response fields change.

To recheck the saved session without another login:

```bash
npm run instagram:check
```

## 3. Start the local backend

From the root, in a second Terminal:

```bash
npm run instagram:api
```

This uses one Uvicorn process on 127.0.0.1:8000 with access logging off. It registers
GET /v1/me, GET /v1/entertainment/feed and the existing playback resolver. Both
entertainment routes require a real Supabase app bearer, then enforce the bound
owner. Provider session material never travels through the phone/API response.
Another account receives 404 without an Instagram request. Never use a fixture
bearer for this live private connection.

The local factory uses a random cursor signing key; restarting invalidates old
pages. Shared core should inject stable signing material and one catalog instance.
Do not run multiple workers against this process-local demo state. Atlas isn't
required for these live pages and no shared migration is changed.

## 4. Connect the phone/app through a reachable HTTPS API origin

Set EXPO_PUBLIC_API_BASE_URL to the HTTPS API origin that serves the assembled
routes. Do not put localhost/127.0.0.1 as a phone's remote backend address. Keep
the app's HTTPS and token verification checks enabled.

```bash
npm run instagram:mobile
```

This clears Metro's saved preview mode and selects the authenticated API feed.
Sign in with the same app account used in step 2; Explore the demo deliberately
uses fixtures. Only five metadata records are requested at a time. The app
prefetches with three or fewer clips remaining while foregrounded/focused,
preserves the current clip on page failure, and evicts already-passed cards as
its 100-record window fills. Exactly one native player remains active, with one
paused upcoming media buffer.

If using the existing development proxy instead of a deployed backend, it forwards
only the existing allowed GET routes to fixed loopback port 8000. Activating it
through a public Expo tunnel forwards app bearer tokens and personalized metadata
through that tunnel provider. The earlier decision requires the user's specific
approval before the agent enables that private transport. These scripts do not
start a public tunnel automatically or embed the connection file/saved catalog.

## 5. Acceptance and recovery

- Verify at least two account-session pages with additional unique Reels; record
  counts, not private post URLs or raw provider responses.
- On the actual phone, pass the original four clips and several five-item pages.
  Test a background/resume, single audio source, and recoverable failed/expired clip.
- Retry a page after a transient failure: it must not silently skip another page.
  Retry clip can request fresh provider metadata for an already-issued video ID.
- If Instagram has no new clips in bounded empty/duplicate windows, automatic
  traversal stops and offers retry. There is no unbounded request loop.
- Reconnect errors are 409, not Supabase 401: the app account stays signed in.
  Transient failure cooldown is 30 seconds; rate-limit cooldown is five minutes.
  Loaded playable clips remain available. Older/expired page cursors require Reload.

## Actual commands available for independent checks

```bash
PYTHONPATH=services/api .local/instagram-probe/venv/bin/python -m unittest discover -s services/api/app/modules/entertainment/tests -v
PYTHONPATH=services/api .local/instagram-probe/venv/bin/python -m unittest discover -s services/api/app/modules/entertainment/experiments -p 'test_*.py' -v
npm run typecheck
npm test
npm run contracts:check
```

All automated provider/auth responses in those tests are synthetic. They validate
owner isolation, retry stability, leftovers/deduplication, bounded 250-clip scrolling,
request serialization, session-file permissions/redaction, checkpoints and renewal.
They do not establish live Instagram/phone acceptance. See the
[integration decision](decisions/adi-live-instagram-feed.md) for the shared handoff.
