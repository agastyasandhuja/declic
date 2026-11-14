# Adi status

## Demo Supabase scope — November 14, 2026

User explicitly deferred fixing the confirmation redirect and configuring custom
SMTP for this demo. Accepted flow: confirm the email when delivered, then return
to the app and sign in manually even if the final localhost page fails. Existing
confirmed demo accounts can continue signing in; broader signup/email-delivery
acceptance is deferred. Email confirmation remains enabled.

The preceding read-only dashboard inspection found no Storage buckets, a 50 MB
per-file upload limit, Site URL http://localhost:3000 with no allowed redirects,
email signup/confirmation enabled, and custom SMTP off. No Supabase settings,
credentials or permissions were changed. Priorities remain the private
lesson-videos bucket and authenticated backend/app integration. Academic source
Storage remains an Amogh handoff. This update changes documentation only;
`git diff --check` passed. No code tests were rerun.

## Hosted Atlas initialized — November 14, 2026

**The shared database foundation is now hosted and verified.** The user selected
Free/M0, corrected the database-user credential locally, and completed a read-only
check at 2026-11-14T16:20:16.699698+00:00. No credential values appear in this file.
This section supersedes earlier pending-credit/failed-authentication checkpoints.

### Changes applied and actual results

1. Ran `PYTHONPATH=services/api .local/atlas-readiness/venv/bin/python -m
   app.modules.auth.atlas_preflight --env-file services/api/.env
   --apply-owned-drafts --write-test` against Atlas `hackumass`.
   **PASS**: app_profiles and entertainment_catalogs created; strict validators,
   unique owner indexes and catalog TTL match the owned drafts. Majority commit,
   snapshot rollback and exact synthetic probe cleanup passed.
2. Read latest Agastya source at 36fbc201228cfad0055cc895b4d8af02930c509f.
   Fetched it without switching/merging branches; exported an ignored source
   snapshot under .local/atlas-readiness/shared-snapshot-36fbc201. Verified the
   migration/config/database/collection/video-repository source blobs against Git
   hashes. No shared Python source, manifest or ordered migration was edited.
3. Installed only the missing pydantic-settings 2.16.3 and python-dotenv 1.2.4
   into the isolated Atlas environment, matching Agastya's lock. Driver remains
   PyMongo 4.15.5. `pip check` passed.
4. Ran `.local/atlas-readiness/venv/bin/python
   .local/atlas-readiness/bootstrap_shared.py` in read-only planning mode.
   **PASS**: source hashes match, target is hackumass, shared namespaces are fresh,
   existing Adi schemas match. Existing unrecorded shared schema would stop setup
   for review rather than be overwritten.
5. Ran the same wrapper with `--apply`, executing the unmodified owner's
   `apply_ordered(database, include_videos=True)`.
   **PASS**: 001_api_learning_runtime (12 API collections), then 002_video_indexes
   (3 video collections). Both markers are present; core startup migration check
   passes. All core validators/indexes and required video indexes match source;
   Adi schemas are unchanged and unrelated collections are preserved.
6. Ran final owned preflight with `--write-test` at
   2026-11-14T16:30:48.734149+00:00.
   **PASS**: actual Atlas connection, replica set/sessions, both Adi schemas/indexes,
   both core migration markers, commit, rollback and probe_cleanup are true.
   `owned_draft_apply_requested=false` here means no second apply was requested.
7. Separate hosted api_jobs checks at 2026-11-14T16:30:52.767932+00:00:
   **PASS**: invalid document rejected with 121; duplicate scoped dedupe key
   rejected with 11000; both synthetic transactions aborted and no synthetic jobs
   remain. No real jobs, private course records or provider outputs were inserted.
8. Owned wire-validator drift check and `pip check` passed. No code change
   required a mobile rerun. Documentation, Git-ignore and credential-marker
   checks passed before the handoff commit.

### Handoff and remaining work

- Shared client/migration assembly stays with Agastya; existing published commands
  were executed, not rewritten. Teammates use server-only MONGODB_URI and
  MONGODB_DATABASE=hackumass. Secrets remain in local/deployment configuration,
  not Git or the phone. No teammate messages, invitations or credentials were sent.
- The saved bootstrap credential has broad database permissions. Create a
  dedicated runtime identity scoped readWrite to hackumass before API deployment;
  no role grants/changes were made automatically. Current workstation access
  works, but deployed backend egress/IP configuration remains to be set.
- Amogh's current published status still uses a local JSON academic store; his
  Atlas persistence/collection drafts remain his task. No academic schemas were
  invented or changed here. No Canvas/Gemini or generation services were invoked.
- API hosting, owner-adapter registration, Supabase private Storage authorization,
  actual authenticated app/API flow and physical-iPhone acceptance remain open.
  Hosted database readiness does not establish those integrations.
- Redacted local evidence: .local/atlas-readiness/report.json,
  shared-bootstrap-report.json and shared-constraint-report.json, all mode 0600.
  Bootstrap snapshot/helpers remain ignored. The backend .env stays mode 0600
  and ignored. No raw URI/password, personal catalog or media was staged.
- Runbook updated at [ADI_ATLAS_SETUP.md](../ADI_ATLAS_SETUP.md).

## Hosted Atlas authentication diagnostic — November 14, 2026

The user proceeded with a Free cluster after credits were unavailable and ran the
local hidden-password setup helper. Server-only configuration was saved in the
ignored services/api/.env; no credential values are included here.

- One read-only authenticated ping reproduced a live Atlas **8000 authentication
  rejection** before any schema inspection or migration. The saved hostname/user
  match the user's screenshot, database matches `hackumass`, a password is present
  and it is not the placeholder. This confirms a credential/authentication issue;
  the exact cause (wrong password, nonexistent/changed database user, etc.) still
  requires correcting the database-user credential. No raw provider message,
  URI or password was displayed.
- Corrected the preflight classifier: Atlas 8000 messages matching authentication
  failure map to AUTH_FAILED; permission failures map to ACCESS_DENIED; other
  8000 failures stay generic. Classification inspects fixed phrases only in
  memory and never exports the provider payload.
- Prepared an ignored, local-only --replace-password helper path. It updates only
  the URI for the same selected cluster/user, preserves other .env settings,
  URL-encodes the entered password and writes mode 0600 atomically. The actual
  saved credential was **not changed** by the agent. The user must enter it in
  their own Terminal. No password reset or Atlas access change was performed.
- Seven focused auth/configuration tests passed, including the new 8000
  credential-vs-permission regression with credential redaction. Standalone local
  helper checks passed for URL encoding, owner-only permissions, preservation of
  unrelated settings, default overwrite protection and refusing a different
  target. `git diff --check` passed. Existing MongoDB integration checks were not
  rerun for this classification-only change; no local test server was started.
- Hosted connection remains unsuccessful. No collections, records, indexes or
  migrations were written by the diagnosis. Next: user re-enters the correct
  database-user password locally, then the helper runs the read-only check again.

## Atlas provisioning preparation — November 14, 2026

User direction: Adi may handle shared cloud provisioning while preserving teammate
workflows. The user is applying for the GitHub Education student pack/credits and
asked to defer connecting/provisioning until access is ready. **No Atlas project,
cluster, database user, IP rule or cloud connection was created.**

- Inspected the latest published `feature/agastya-learning-engine` snapshot
  `c84f6d1ec2c2f7c45b1b85b3721d50711c95a5c5`, including AGASTYA_API status,
  config/database/migrations, pyproject and uv.lock. Agastya's shared runtime and
  ordered migrations **already exist there**. Earlier notes below describe this
  checkout's older state. Shared runtime/driver/migration ownership stays Agastya's;
  Adi takes Atlas project/cluster/access/connectivity preparation only.
- Confirmed environment names MONGODB_URI / MONGODB_DATABASE and shared default
  database `hackumass`. Matched Adi's owned .env.example and dev lock to that
  default and the existing PyMongo **4.15.5** pin. FastAPI 0.162.7, httpx 0.28.1,
  jsonschema 4.26.0 and Pydantic 2.14.3 match the inspected shared lock. Existing
  local provider environments were preserved; no shared manifest was changed.
- Added [Atlas runbook](../ADI_ATLAS_SETUP.md) and an owned standalone preflight
  command. Default mode is read-only; explicit flags reuse owned additive setup
  and verify majority commit/snapshot rollback in a fresh synthetic collection,
  cleaning up only that collection. URI/password/raw driver errors are withheld;
  reports are ignored, mode 0600. TLS verification is required for Atlas URIs.
- Added validation-enforcement checking. Existing conflicting validator/warn/off
  policies are refused rather than silently rewritten. No core/video/academic
  collection or migration is edited by this helper.
- Confirmed permission split from official docs and actual migration source:
  runtime readWrite on hackumass; migration readWrite+dbAdmin on hackumass because
  Agastya's runner uses collMod. Proposed narrow network/project/user choices are
  documented for later review, not applied. No paid tier/credits were used.
- Searched available integrations and suggested MongoDB Atlas; it was not
  installed/connected when checked. Browser fallback reached the Atlas login
  page. After the user deferred setup, that temporary tab was closed. Existing
  Supabase tabs and the user's education application were untouched.
- Dependency handoff: promote jsonschema from shared dev to runtime dependencies
  when mounting Adi's modules. Core injects Database.mongo into Adi repositories;
  its wrapper is not itself a PyMongo Database. No teammate messages were sent.
- Remote Adi branch was renamed to `adi-private-phone-feed`; confirmed with
  git ls-remote. This preparation is on `codex/adi-atlas-readiness`, preserving the renamed
  delivery branch and teammate feature branches.

Actual verification in isolated `.local/atlas-readiness/venv`:

```bash
MONGODB_TEST_URI='mongodb://127.0.0.1:27028/?replicaSet=adi_atlas_preflight' PYTHONPATH=services/api .local/atlas-readiness/venv/bin/python -m unittest discover -s services/api/app/modules/auth/tests -v
```

**13/13 passed** on a temporary real MongoDB 8.0.38 replica set with PyMongo 4.15.5.
This includes the five existing database/HTTP checks, three auth checks, three
preflight configuration/redaction checks and two real preflight checks. Full CLI
flags, read-only preservation, repeatable owned setup, synthetic transaction
commit/rollback/cleanup and refusal to overwrite an existing validation policy
were verified. `--help`, `pip check`, wire-validator drift check and `git diff
--check` passed. This is local compatibility evidence, not hosted Atlas acceptance.
The dedicated loopback test server was stopped after testing.

Next when credits/access are ready: select/reuse the team project, review the
Free/M0 deployment and exact database/network grants, configure server-only URIs,
run hosted preflight, and apply Agastya's existing ordered migrations from his
integrated runtime. Actual live Atlas transaction/TLS verification remains open.

## Current A1–A3 delivery — November 14, 2026

The independent implementation through A3 is substantially built and locally
verified. **A1/A3 are not accepted on a physical iPhone; Atlas cloud is not
provisioned/connected.** The private Instagram phone handoff remains paused. This
section supersedes older scaffold/deferral statements in the historical log below.

### Delivered code

- A1: Expo workspace, Supabase auth UX/session provider and secure storage already
  existed. Added safe transient-refresh behavior (outage does not sign out), a
  response-body API deadline, normalized-path/origin checks, strict safe error
  fields and an explicit corrupted-session clearing action. Session restore still
  uses the existing SDK storage key, preserving installed sessions.
- Backend: SupabaseVerifier, bearer dependency and identity/entertainment router
  factories. Authentication derives the subject from Supabase's canonical get-user
  result; editable metadata/email/query/body IDs cannot impersonate another user.
  Remote auth outages are retryable 503; missing/forged tokens are 401. Safe errors
  and no-store responses are demonstrated in the local experiment assembly.
- Identity persistence: injected ProfileRepository, one app_profiles document per
  subject, unique owner index, strict validator, IANA timezone/name validation,
  atomic expected_revision edits and 409 conflicts. GET/PATCH /v1/me are exported;
  no second password system or duplicated authoritative Auth email is introduced.
- Entertainment persistence: injected CatalogRepository/CatalogService and an
  explicit fixture repository. One atomic private batch per subject, max 100
  normalized clips/32 KiB each, 60–86400-second retention, unique owner and TTL
  indexes. Reads check owner and expiry before returning records. Normalization
  strips provider credentials/unknown raw fields and rejects credential URLs.
- A2: cached feed pagination no longer truncates the rest of a small batch. HMAC
  cursors bind subject, size and batch revision; stale batches return 409 and
  foreign/tampered cursors 422. Expired/unavailable resources return 410 playback
  outcomes. The user-run probe now supports explicit --pages 2 (max 3), with
  deduplication, cursor traversal/end/repeat guards and bounded requests. This new
  provider pagination code has **synthetic** tests only; no new Instagram login or
  retrieval was attempted. The prior four-Reel live evidence remains separate.
- A3: two bounded native media buffers, exactly one granted active playback and
  one VideoView; standby stays paused. Preferred upcoming forward buffer is five
  seconds (an OS buffering preference). Per-slot serialized replacements, stale
  guards, synchronous visibility/background gating, layout-phase cleanup and
  15-second load/post-load-stall recovery. Reload releases both native players.
- Watch time measures media-position movement bounded by wall time, excluding
  stalls, seeks, long sample gaps, hidden/background intervals. Swipes/accessible
  paging emit distinct skip observations. Observations remain local; A4 server
  session/event delivery is not implemented. Attribution/source links, accessible
  next/reload controls, cancellable pages, stale-cursor reload and stable card
  indexes across expiring older URLs are present. Metadata is capped at 100.
- Database domain manifests/backfill notes, wire-derived validator generator,
  backend .env.example, isolated pinned development dependencies and exact setup
  guides are supplied. Shared API main/core, shared Python manifest/migrations,
  teammate packages and their collection drafts were not edited.

### Verification actually performed

| Command/check | Result and limit |
|---|---|
| npm run typecheck | PASS, strict TypeScript. |
| npm test | PASS, 29/29. Includes storage, auth/API refresh and body timeout, buffer promotion/exclusivity/races, watch/stall accounting, source dedup/index stability, private preview gates and a synthetic loopback proxy test. |
| npm run contracts:check | PASS, generated TypeScript matches owned v1 schemas. |
| python3 database/domains/entertainment/generate_validator.py --check | PASS, nested Mongo validator matches the v1 wire schema. |
| PYTHONPATH=services/api .local/instagram-probe/venv/bin/python -m unittest discover -s services/api/app/modules/entertainment/experiments -p 'test_*.py' -v | PASS, 13/13. Probe/fake-provider pages, credential-safe failure reports, ASGI auth/ownership, finite-batch cursor/expiry behavior. No live provider session in these tests. |
| MONGODB_TEST_URI=mongodb://127.0.0.1:27018 PYTHONPATH=services/api .local/instagram-probe/venv/bin/python -m unittest discover -s services/api/app/modules/auth/tests -v | PASS, 8/8: three auth/config tests plus five real local MongoDB tests. Actual validator/unique/TTL-index creation, repeatable drafts, profile CAS/ownership, atomic cache/stale cursors/expiry and HTTP profile/catalog routes. HTTP Auth transport is synthetic. |
| .local/instagram-probe/venv/bin/python -m pip check | PASS, no broken requirements. |
| npx expo-doctor@latest (apps/mobile) | PASS, 20/20. |
| HACKUMASS_INSTAGRAM_PREVIEW=1 HACKUMASS_PREVIEW_API=0 npx expo export --platform ios --output-dir /private/tmp/hackumass-adi-a3-verified-ios | PASS, final release bundle exports with private preview gated out. Private-catalog markers: zero in release/source; actual public key: zero in reviewable source. The publishable config is expected in the built app. |
| Configured Supabase canonical user endpoint with synthetic invalid bearer | Actual network result 401 AUTH_INVALID; no valid user/token was requested or guessed. This is not successful real-account protected API acceptance. |
| Public replacement fixture one-byte Range GET | HTTP 206 video/mp4, Content-Range present; no downloaded media file. |
| git diff --check | PASS at code checkpoint; repeated before commits. |

MongoDB Community 8.0.38 ARM64 came from the official vendor archive; SHA-256
5c372533187a7789b6b2f4d7856f0651557dfbed572dbe5f4c23f43578fc74df was verified.
It ran temporarily on 127.0.0.1:27018 with data/logs under /private/tmp. Tests
create/drop only fresh adi_test_<random> databases, never application data. No
system service was installed. This is actual MongoDB, **not Atlas cloud**. Driver
pymongo 4.17.0 was installed only in the ignored isolated environment.

The initial Python discovery command lacked PYTHONPATH and failed to import app;
the exact corrected commands above pass. The sandbox denied loopback binding for
MongoDB/proxy tests initially; permitted loopback execution passed. These setup
failures are not reported as passing runs.

### Simulator observations

- Started only ordinary fixture Expo on localhost:8081 with both private flags
  disabled; the old cached private simulator bundle was reloaded to public
  fixtures. No public Expo tunnel/private API was started.
- Traversed the five-card fixture feed using accessible next/skip controls; the
  second fixture page loaded. Recovered from the deliberately missing first clip.
  Found and fixed two actual UI races: stale status from the prior player and a
  visibility gate left paused by batched updates. Rechecked the recovery path.
- The fourth original test asset advanced time but rendered black. Replaced it
  with reachable shortform_1.mp4; native image rendering and 78s/107s measured
  activity were observed. Third/fifth clips rendered too; fifth reached 24s.
- Native app background/resume retained 39s, then resumed from that value rather
  than adding the background interval. Leaving the feed for The lab stopped local
  activity updates. Manual pause displayed Play video. This is simulator evidence,
  not physical-iPhone audio/performance acceptance.
- Device Hub's drag/scroll automation returned noWindowsAvailable; accessible
  paging exercised FlatList transitions instead. Sustained real swipe gestures
  still require the device acceptance below. No alternative UI control tool was
  used to bypass that limitation.
- Screenshot: /private/tmp/hackumass-adi-a3.png. Unavailable mode was turned off and
  the ordinary fixture app was left manually paused. Later code-only hardening
  (stable expiry indexes/lazy URL resolve) passed typecheck/tests; actual renewed
  provider media is still unverified. The final hardened build also rendered the
  first fixture and accumulated 171s; it was manually paused and backgrounded.
  Expo and temporary MongoDB were then stopped. lsof confirmed no listeners on
  8081/27018; restart using the run guides rather than an old tunnel URL.

### Delivery commits

- c47d327 — verified identity, owned MongoDB persistence, API/probe tests and setup.
- f5b33a7 — buffered mobile playback, source/session/API recovery and mobile tests.
- This status/task update records exact results and the remaining owner/device work.
- Delivery branch: codex/adi-private-phone-feed in hackumass-14. No main merge or
  teammate message is part of this delivery. No actual .env, private catalog,
  provider session, downloaded media or application DB data was staged.

### Teammate readiness and exact handoffs

Amogh can build immediately with the existing mobile FeatureScreenProps, SDK
user.user_id, authenticated ApiClient, theme and app-owned navigation slots.
Use the synthetic demo for independent UI. Academic persistence, source/Storage
policy work and package exports remain Amogh's ownership; no real course data was
loaded. The UUID subject, never an email, is the cross-domain ownership key.

Agastya can integrate the exported factories/repositories now. Concrete assembly:

```python
verifier = SupabaseVerifier(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
current_user = make_current_user(verifier)
profiles = ProfileRepository(shared_database)
catalog = CatalogService(CatalogRepository(shared_database), cursor_secret=server_key_bytes)
app.include_router(create_identity_router(current_user, profiles))
app.include_router(create_entertainment_router(current_user, catalog))
```

Core supplies safe common error handlers, a bounded shared PyMongo client/lifetime,
the same >=32-byte server-only cursor key on all replicas, Atlas secrets and HTTPS
hosting. Fold owned manifests into ordered migrations; do not silently tighten
other collections. Runtime dependency requests: fastapi 0.162.7, httpx 0.28.1,
jsonschema 4.26.0, pymongo 4.17.0; local runner uvicorn 0.54.0. instagrapi 3.2.12
is optional provider experiment work. No messages were sent to teammates.

Run guides: apps/mobile/README.md, services/api/app/modules/auth/README.md,
services/api/app/modules/entertainment/README.md. The local fixture API verifies
real app tokens but serves explicitly synthetic clips; it does not depend on
Canvas, generation or MongoDB. Production assembly remains with Agastya.

### Remaining setup / acceptance

1. **Atlas cloud:** no MONGODB_URI/database or connected Atlas account/CLI is
   configured. Agastya still provisions the cluster, backend-scoped DB access,
   shared client/manifest and ordered migrations; Amogh/Agastya add their owned
   collections. Owned Adi schemas/repositories are locally tested. Private
   Supabase Storage buckets/policies/signed asset authorization remain shared
   backend/domain work; no buckets or policies were claimed ready.
2. **A1 real account:** user reported signup/email/login on the phone. Controlled
   authenticated device restart, logout/private-state clearing, invalid credentials,
   offline recovery and a successful protected /v1/me call remain open. Project
   confirmation redirect/deep-link allowlisting needs production configuration;
   email confirmation stays enabled.
3. **A2 live provider:** existing four-Reel retrieval/relevance evidence is valid.
   New real pagination, URL renewal, continued personalization and each clip on
   the physical phone require a fresh user-run provider session. No password,
   cookie or resumable provider session is stored by the probe.
4. **A3 physical iPhone:** sustained gesture paging, one audible source,
   background/resume and unavailable recovery must still be observed there.
   Simulator/fake-driver evidence is not acceptance. No Android/TestFlight claim.
5. **Private phone handoff:** keep paused. App owner UUID has not been supplied;
   the earlier email is not used to authorize. Automatic approval review rejected
   exposing the private catalog via the public Expo tunnel because that specific
   data transfer was not approved. It remains disabled; no private batch was
   exposed. Resume requires the exact app subject and specific transfer approval.
6. **A4 remains future scope:** unified feed/session/event submission, course and
   quiz components, quiz gating and revision-based recommendation changes await
   the owners' exports. No parallel recommender or fake generation was added.

## Earlier private-phone pause checkpoint — November 14, 2026

The user asked to pause after a Bad Gateway error during the physical-phone
handoff. The private-phone handoff remains paused; the later independent A1–A3 goal resumed implementation and database preparation.
Phone Expo/tunnel, simulator Expo and the loopback preview API processes were
stopped. Keep the working tree intact; unfinished work is **uncommitted** on
`codex/adi-private-phone-feed`, based on pushed preview commit `bdc5139`.

Resume checkpoint:

- Instagram retrieval and saved-batch simulator playback are verified as recorded
  below. The phone initially opened the public fixture app through the Expo HTTPS
  tunnel, confirmed by the user and a connected iPhone debug target. Instagram
  clips have **not** been delivered to the physical phone.
- The user created an app account, received the confirmation email, hit a
  localhost redirect error, then successfully signed into the Expo app. This is
  user-reported real signup/email/login evidence; restart persistence, logout,
  invalid credentials and offline behavior still need actual acceptance tests.
- Added (uncommitted) Adi-owned auth service/router, owner-scoped saved-catalog
  service/router, and temporary local FastAPI assembly under entertainment's
  experiments. Supabase Auth verifies bearer tokens remotely; catalog access
  checks a server-local owner subject before reading private data. No Atlas,
  shared API core/main or Agastya-owned manifest was changed.
- Added (uncommitted) an opt-in Metro transport proxy to fixed localhost:8000,
  an Expo HTTPS-origin helper, dynamic app config, and a selectable App user ID
  in The lab. expo-constants was added via Expo's compatible installer; JS
  manifest/lockfile changes are part of this unfinished branch.
- Isolated Python environment additionally installed FastAPI 0.162.7, uvicorn
  0.54.0, httpx 0.28.1 and jsonschema 4.26.0. These dependencies still need a
  documented handoff to Agastya; no shared Python manifest was edited.
- Already-started checks finished before shutdown: TypeScript passed, JS tests
  19/19 passed, generated-contract check passed, Python probe/API tests 9/9 passed.
  Real loopback API calls without a token and with an invalid token both returned
  401 (AUTH_REQUIRED / AUTH_INVALID). Accepted authenticated access and real
  cross-account isolation are not live-validated; ownership tests used fakes.
- Owner binding is unfinished. The user provided an email when asked for the
  app user ID; no UUID was obtained, and no owner.json was created. Do not bind
  ownership from email or expose the catalog to the first authenticated caller.
  Obtain the UUID displayed in The lab, validate it, and save it only to ignored
  .local/instagram-probe/owner.json with private permissions on resume.
- Automatic approval review rejected enabling HACKUMASS_PREVIEW_API=1 through
  Expo's public tunnel: the specific transfer of private recommendation metadata
  and signed media URLs through that external destination lacked explicit user
  approval. No workaround was attempted. The restored sample tunnel had the
  private API disabled. Before enabling private exposure, finish reviewable docs /
  local checks and obtain explicit approval for that concrete transfer.
- The tunnel hostname changed after restarting. On resume, start the intended
  approved mode and generate a fresh QR from the actual running URL; do not reuse
  old QR images. The last phone error was Bad Gateway; its exact cause remains
  unresolved. Keep private catalogs, account identifiers, tokens and provider data
  out of Git. Review the temporary assembly/proxy integration impact in a proposed
  decision and update setup/status before committing this unfinished work.

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
