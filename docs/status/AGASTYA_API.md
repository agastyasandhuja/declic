# Agastya — API and recommendations

November 14, 2026. Independent API runtime implemented and locally verified;
live owner adapters, Atlas deployment, and device integration remain pending.

## Scope and collaboration

- Implemented API core/configuration, shared MongoDB lifecycle, API-only collection
  setup, feed sessions/events/recommendations, quizzes/progress, and shared jobs/outbox.
- Adi's auth/entertainment/mobile and Amogh's Canvas/curriculum modules are external
  adapter boundaries. The API does not implement their provider integrations.
- Video generation, narration/captions, renderer, and video publication remain in
  the other chat. This stream supplies read interfaces and a reference-only
  reteaching request; it does not run a second generation pipeline.
- Preserved existing worktree changes and branch. No commit, reset, clean, or
  branch switch was performed by this chat.
- An early `ruff check app --fix` was too broad while video files were appearing
  concurrently. All subsequent lint/format commands target explicit API-owned
  paths. No intentional video implementation changes were made here. Because
  those files were untracked and concurrently written, that early command's
  possible import-only edits cannot be distinguished from the other chat's edits.
- Initially used the scaffold's Postgres proposal. When the shared instructions
  adopted Atlas during this work, removed SQLAlchemy/Postgres application code
  and changed the runtime to PyMongo. The remaining SQLite code is an explicit
  durable synthetic document-store fake, never a production option.
- Isolated final API tests/dependencies at `/private/tmp/hackumass-api-runtime` so
  later installs do not change the concurrent video environment. Recommended
  persistent environment is `services/api/.local/api-venv`.

## Implemented behavior

- One FastAPI assembly with protected feed/quiz/progress routes, current-user
  dependency, safe error envelope/request IDs, bounded request bodies, CORS
  allow-list, and database-backed per-user request limits.
- Explicit identity seam; absent identity fails closed, fixture identity is
  prohibited in production, and no client-supplied user ID establishes ownership.
- MongoDB retryable transactions, majority writes, snapshot reads, scoped unique
  indexes, validators, explicit repeatable setup, and startup migration check.
- Durable session resume, opaque owner/session/revision/page-size-bound cursors,
  retry-stable occurrence IDs, bounded prefetch, and cached-page media revalidation.
- Deterministic course → objective → variant ranking: progressive 10/20/35/50%
  study targets, bounded slot debt, course fairness, exam evidence/date precision,
  mastery/review/novelty, prerequisites, recent exposure penalties, and alternate
  formats/approaches. Unready/private/expired/incompatible assets are excluded.
- Playback event deduplication, issuance/owner checks, timestamp/progress bounds,
  foreground-only credited time, and exposure tracking without invented mastery.
- Quizzes after sufficient exposure; prefetch does not activate a gate. Valid
  answers unlock regardless of correctness. Attempts, learning state, revisions,
  idempotency results and outbox event commit together. Recovery stays ungraded.
- Unique job enqueue, concurrent claims, lease fencing/heartbeat, bounded retries,
  cancellation, terminal exhausted leases, and sanitized diagnostics.

## Commands and observed results

Commands ran from `services/api` unless noted. Final Python tooling below is from
`/private/tmp/hackumass-api-runtime/bin`; dependency installation used uv with the
checked-in `uv.lock`. The installed package set was isolated for final checks.

1. `pytest -q tests/test_api.py tests/test_policy.py tests/test_jobs.py
   tests/test_playback_events.py tests/test_boundaries.py tests/test_contracts.py`
   — **32 passed, 1 skipped** using the explicit SQLite JSON fake. The skipped
   test requires real MongoDB collection validators/indexes.
2. The same command with
   `API_TEST_MONGODB_URI=mongodb://127.0.0.1:28071/?replicaSet=hackumass_api_test`
   — **33 passed** against an actual temporary MongoDB 8.0.38 single-node replica
   set. Each test used a random `api_test_*` database, removed at teardown.
   Covers concurrent grading/enqueues/claims, transaction rollback, durable job
   restart, lease loss, repeated setup, unique indexes, and document validation.
   This verifies local MongoDB behavior, not hosted Atlas connectivity/TLS.
3. Scoped Ruff lint with `--config services/api/pyproject.toml` — **passed** for core/main/workers/recommendations/quizzes,
   the six named API test modules/conftest, migration entry, and API scripts.
4. From repository root: `python scripts/export-api-contracts.py --check`
   — **13 generated schema/index artifacts match runtime definitions**.
5. `python scripts/simulate-api-session.py` — synthetic ASGI session reached
   **750 active-view seconds**, all four density targets, **50 video slots**,
   **15 study slots (5 per course)**, **6 submitted quizzes**, one wrong-answer
   unlock, and **12 alternate-explanation slots**. No real media was played.
6. Actual Uvicorn factory startup and HTTP smoke, temporary localhost port:
   `/health` returned ok; authenticated session creation and feed returned
   **10 items including one study item**. Temporary HTTP process stopped afterward.
7. `git diff --check` passed for tracked changes. Runtime schemas and all added
   source files were checked with the scoped formatter/linter.

The first policy tests found fractional study debt being discarded and cumulative
course exposure drifting. Both were corrected and the suite rerun. A cached empty
page now refreshes when inventory arrives; cached media is reauthorized/refreshed
before replay. A Starlette TestClient deprecation warning about httpx remains;
it did not fail tests or affect the HTTP smoke test.

The test MongoDB binary was downloaded from MongoDB's official distribution and
matched its published SHA-256. It used only synthetic data under `/private/tmp`
and API-only localhost port 28071. An occupied port 27019 was left to the other
workstream; no successful initialization or database writes were made there.
The API-only test server was shut down after verification; its process exited 0.

## Interfaces and artifacts

- [API runbook](../../services/api/README.md)
- [Detailed handoff](../../services/api/API_HANDOFF.md): exact auth/catalog/academic/
  quiz consumer adapters, mobile event semantics, quiz lifecycle and worker hooks.
- [Runtime decision](../decisions/002-api-learning-runtime.md)
- [Generated public schemas/OpenAPI](../../contracts/schemas/feed/README.md)
- [Synthetic API catalog](../../fixtures/feed/api-catalog.json): three subjects,
  20/4/2 variant inventories, explicit/date-only/unknown assessment evidence;
  `fixture.invalid` media URLs are not playable.
- [API collection validators/indexes](../../database/domains/learning/api-runtime-v1.json)
  and ordered `database/migrations/001_api_learning.py`.
- `Worker.register(job_type, handler)` and `JobContext.heartbeat` are public worker
  hooks. `learning.reteach.requested` carries objective/quiz/revision references;
  its generation handler is deliberately not implemented by this chat.

## Remaining integration work and limits

### Follow-up: withdrawn-media buffer recovery

- Reproduced a session deadlock: fill the 40-slot prefetch buffer, withdraw a
  cached page's media, then restore inventory. Removed occurrences still counted
  toward the buffer, so replacement requests returned `FEED_BUFFER_FULL`.
- Fixed only the recommendation service: withdrawing an occurrence now marks it
  terminal. It receives no watch time, exposure, or mastery credit; late playback
  events remain rejected with `ITEM_UNAVAILABLE`. The normal buffer cap still
  applies to replacement items.
- Added an HTTP regression in `tests/test_boundaries.py`; observed its failure
  before the fix. Full six-module API suite now reports **33 passed, 1 skipped**
  on the explicit fixture adapter. Scoped Ruff, all 13 schema artifacts, and
  `git diff --check` pass.
- Ran `pytest -q tests/test_boundaries.py -k 'withdrawn or unbounded_prefetch'`
  against a fresh temporary real MongoDB replica set: **2 passed, 6 deselected**.
  Initial sandbox execution could not bind a localhost socket; the approved
  local test run succeeded and its MongoDB process exited 0 after cleanup.
- Current source inventory confirms auth, entertainment, Canvas and curriculum
  directories contain only their `AGENTS.md` files. Their real adapters therefore
  cannot yet be wired or verified here without taking over another owner's work.
  No provider or video-generation files were changed in this follow-up.

### Outstanding owner and deployment handoffs

The video handoff subsequently arrived: `FeedVideoReader` and the video router
now compose through the core factory without changing either owner's module.
Added `tests/test_video_handoff.py` using the actual video service/adapter/router
and its local synthetic repository, with a fake signer. HTTP assertions cover
authorized private/shared study selection, expiry metadata, private route rejection
before signing, and removal of private lesson lineage from shared details.
This is interface integration evidence, not real Storage or media validation.

The video service imports `httpx`, which was previously only a development
dependency of the shared manifest. Moved `httpx==0.28.1` into runtime dependencies
and regenerated `uv.lock` offline without changing the video requirements file.
An isolated `uv sync --locked --offline --no-dev` installation under
`/private/tmp/hackumass-api-import-runtime` successfully imported core and the video
service/adapter/router. `pytest -q tests` now reports **34 passed, 1 skipped**;
the skip requires MongoDB. Scoped Ruff and all 13 generated schemas pass.

- Wire Adi's real token verifier and entertainment adapter, Amogh's current
  authorized academic reader, and a real quiz-definition reader. Video catalog
  composition is now tested with synthetic persistence and signing.
  No real token verification, provider retrieval, Canvas import, video playback,
  signed Storage access, or iPhone behavior is claimed by these tests.
- Connect owner domain routers through `create_app`; their APIs are not invented
  or replaced here. Video-detail/playback routes remain with the videos owner.
- Resolve authorized current lesson plans before the video integrator consumes
  reteaching jobs. The video owner's index initialization is now assembled into
  ordered setup; hosted deployment remains unverified.
- Configure Atlas credentials/network access and the deployment's HTTPS/proxy
  settings; apply API setup with the appropriate database permissions. The
  checked-in environment example contains placeholders, not credentials.
- Run the real multi-course/mobile acceptance scenario after those adapters are
  available. Local fixture and replica-set results are not substitutes.

### Ordered setup verification and completion audit

- Added `002_video_indexes.py` and the explicit
  `python -m app.core.migrate --apply --include-videos` composition command.
  Migration 001 runs first; 002 delegates to the unmodified video owner's
  `AtlasVideoRepository.initialize()`. The default command remains API-only.
  Completion is recorded only after the owner's initializer succeeds.
- Added `tests/test_migrations.py`. Actual temporary MongoDB checks prove opt-in
  behavior, repeatability, preservation of an unrelated synthetic collection,
  uniqueness enforcement, predecessor ordering, and failure/recovery without
  silently deleting duplicate records or falsely recording success.
- `pytest -q tests` against a fresh temporary local MongoDB replica set:
  **38 passed** in 28.78 seconds. The same suite on the explicit fixture adapter:
  **34 passed, 4 skipped** (MongoDB-specific checks). Scoped Ruff, CLI `--help`,
  all 13 schema artifacts, and `git diff --check` passed. Temporary MongoDB and
  its verification process both exited 0; no hosted database was accessed.

| Required API outcome | Current evidence | Remaining condition |
|---|---|---|
| Core configuration, authenticated ownership boundary and router assembly | Core tests and video HTTP composition test | Adi's real token verifier is absent |
| Durable jobs, deduplication, leases, retries and atomic outbox | Local MongoDB concurrency/restart/rollback tests | Domain event/job handlers need their owners' implementations |
| Adaptive course/objective/variant feed | Policy, HTTP, playback-event and synthetic session checks | Real academic and entertainment readers are absent |
| Quiz grading, unlock, recovery and learning revision | Idempotency/concurrency/gate tests | A scoped real quiz-definition producer is absent |
| Video feed and playback interface | Actual owner adapter/router tested with synthetic persistence and signer | Real published inventory and Storage signing/playback are unverified |
| Ordered database setup | Both migrations verified on temporary real MongoDB | Atlas URI, credentials and network configuration are absent |
| Integrated phone acceptance | No adequate evidence yet | Above adapters, deployed backend and device scenario |

The same external integration blockers have remained across the API recovery,
video-adapter handoff, and ordered-setup continuations. Latest recheck: auth,
entertainment, Canvas and curriculum directories still contain only `AGENTS.md`;
neither local `.env` file nor the process environment has a nonempty MongoDB URI.
Only configuration presence was printed, never secret values. Available
independent API work is implemented and verified; finishing live acceptance now
requires owner deliverables and environment configuration. The full goal remains
unachieved and is blocked, rather than claiming completion or taking over those
owners' implementation. No other owner's source was edited in this continuation.

CodeGuard safeguards used: secrets in environment configuration (never hardcoded),
TLS verification enforced for production MongoDB, CSPRNG IDs/tokens and SHA-256
fingerprints, typed/allow-listed inputs and outputs, scoped queries, atomic
idempotency, and sanitized diagnostics. These protect authentication, private
course state, and retry correctness without implementing another owner's auth.
