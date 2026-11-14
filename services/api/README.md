# Learning API

FastAPI core, adaptive feed, quiz grading/progress, and durable worker infrastructure
are implemented in this stream. MongoDB Atlas is the application datastore;
Supabase Auth/Storage remain separate domain adapters. See [API_HANDOFF.md](API_HANDOFF.md)
for ownership, adapter interfaces, mobile integration, and verification boundaries.

The API can run independently with synthetic adapters. Fixture URLs are deliberately
non-playable metadata. Passing tests does not establish provider authentication,
Canvas ingestion, media playback, live Atlas connectivity, or iPhone integration.

## Install and run the fixture API

Prerequisites: Python 3.11+ and uv. From `services/api`:

```sh
export UV_PROJECT_ENVIRONMENT=.local/api-venv
uv sync --locked
export API_ENVIRONMENT=fixture
export API_PERSISTENCE=fixture_sqlite
export API_FIXTURE_DATABASE_PATH=.local/api-fixture.db
export API_FIXTURE_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
uv run --locked uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Use a separate virtual environment for this API; the concurrent video workstream
has its own requirements and runtime. `.local` and `.env` are ignored by Git.
The fixture token authenticates only `user_demo_01` and is forbidden in production.
Do not use fixture authentication with real student data.

Open `/docs` locally to inspect requests. For example, from a shell with the same
fixture token environment:

```sh
curl -sS http://127.0.0.1:8000/health
curl -sS -X POST http://127.0.0.1:8000/v1/feed/sessions \
  -H "Authorization: Bearer $API_FIXTURE_TOKEN" \
  -H 'Content-Type: application/json' -d '{}'
```

The fixture database is durable across API restarts. Fixture mode is explicitly a
local fake document store backed by SQLite; it is not the production datastore
and does not emulate all MongoDB behavior. Tests also exercise the real driver
against an isolated MongoDB replica set.

## MongoDB and real domain adapters

Set server-only `MONGODB_URI`, `MONGODB_DATABASE`, `API_PERSISTENCE=mongodb`, and the
appropriate `API_ENVIRONMENT`. The URI is never returned/logged. Production
requires TLS with certificate/hostname verification. Use a least-privilege runtime
database user; initialization needs a separate identity allowed to create/modify
collections and indexes. MongoDB must support multi-document transactions.

```sh
uv run --locked python -m app.core.migrate --apply
```

This creates/updates only the `api_*` collections and records migration
`001_api_learning_runtime`. The ordered migration entry point is
`database/migrations/001_api_learning.py`; generated validator/index definitions
are in `database/domains/learning/api-runtime-v1.json`. Startup checks the migration
marker; it never performs production schema changes automatically.

To include the video owner's current index definitions, run:

```sh
uv run --locked python -m app.core.migrate --apply --include-videos
```

This applies API migration 001 first, then delegates migration 002 to
`AtlasVideoRepository.initialize()`. It creates the owner's indexes on
`video_generation_jobs`, `video_variants`, and `video_outbox`, and records
`002_video_indexes` only after success. It does not generate/publish media or
consume the video outbox. Other owners' collections are not initialized here.
Index builds are not one transaction: a failure can leave earlier indexes in
place. Resolve conflicting records explicitly, then rerun; setup never deletes
data to make a unique index succeed.

Inject Adi's verified identity/entertainment adapters, Amogh's authorized academic
reader, and the video chat's ready-catalog/quiz-definition adapters through
`create_app`. Inject domain routers through `domain_routers`. Domain routes use
`core.dependencies.get_current_user`; the Canvas callback uses its own OAuth state.
Production startup rejects missing/fixture identity. No login/password system is
implemented here. Without connected catalogs, the feed honestly reports empty
inventory rather than returning synthetic content in deployed modes.

Run behind HTTPS and configure the trusted reverse proxy explicitly. The phone
must use a reachable HTTPS API URL; `localhost` on the phone is not this laptop.
Deployment/Atlas provisioning and live adapter verification remain pending.

## Implemented HTTP routes

- `GET /health`
- `POST /v1/feed/sessions`
- `GET /v1/feed?session_id=...&cursor=...&limit=5`
- `POST /v1/feed/events` (bounded JSON array)
- `POST /v1/feed/sessions/{session_id}/quiz-gate`
- `POST /v1/quizzes/{quiz_instance_id}/answers` (`Idempotency-Key` required)
- `POST /v1/quizzes/{quiz_instance_id}/recover`
- `GET /v1/learning/progress`

Auth/profile, entertainment, Canvas, curriculum, and video-detail/playback routers
remain with their owners; core can register them without editing their modules.
Feed queries never call a model, renderer, or synchronous generation pipeline.

## Worker commands

```sh
uv run --locked python -m app.workers.main --fixture-echo --once
uv run --locked python -m app.workers.main --registrar your_domain.worker:register
```

The first command is allowed only in fixture/test mode. The second is the explicit
composition seam for an owner-provided registrar; no module of that example name
is shipped. Jobs with no registered handler stay queued. See the handoff for lease,
heartbeat, deduplication, cancellation, outbox, and reteaching request semantics.

## Checks

From `services/api`, in the isolated API environment:

```sh
uv run --locked pytest -q tests
uv run --locked python ../../scripts/export-api-contracts.py --check
uv run --locked python ../../scripts/simulate-api-session.py
```

For the same suite against a real MongoDB replica set, set
`API_TEST_MONGODB_URI` to the test server URI. The suite creates random `api_test_*`
databases and drops only those databases afterward. Never point tests at a server
where that test-database creation/cleanup is not authorized. The app's ordinary
`MONGODB_DATABASE` is not used for tests.

Format/lint only this chat's files; do not run repository-wide auto-fixes while
other agents are working. Validation evidence is in
[Agastya API status](../../docs/status/AGASTYA_API.md).


## Integrated Atlas runtime (November 14)

Run from `services/api` after configuring the ignored server `.env`:
`MONGODB_URI`, `MONGODB_DATABASE`, `SUPABASE_URL`, and
`SUPABASE_PUBLISHABLE_KEY`. Production also requires a stable random
`API_CATALOG_CURSOR_SECRET` (32+ characters). Do not substitute a Storage
service-role key for the publishable auth key.

```sh
uv sync --locked
uv run --locked python -m app.modules.auth.atlas_preflight --env-file .env
uv run --locked python -m app.core.migrate --apply --include-videos --include-identity-catalog
uv run --locked uvicorn app.runtime:create_app --factory --host 0.0.0.0 --port 8000
```

The migration command is an explicit operator action using the migration
credential. It delegates Adi's schemas to his installer; existing conflicting
validators fail without overwriting them. The runtime performs read-only schema
checks and uses the shared MongoDB client for profiles, entertainment catalogs,
feed sessions, quizzes and jobs. It performs no seeding or provider retrieval.
Use a database-scoped runtime credential when serving traffic.

`app.runtime:create_app` mounts `/v1/me`, `/v1/entertainment/feed`, playback,
unified feed, quiz and progress routes. All use the same verified Supabase
subject and core rate limiter. Auth HTTP is asynchronous; synchronous database
work runs in the thread pool. Empty/expired owned catalogs produce an empty
unified feed rather than loading another user's catalog. Catalog records must
first be published through Adi's `CatalogRepository.replace_catalog` service.

`app.main:create_app` remains the injectable fixture/integration factory.
Amogh's academic code is merged and its handoff test passes, but his current
persistence is local JSON, not Atlas. Academic routers and the video Storage
reader are still explicitly supplied through that factory; this entry point does
not claim course-to-video generation or hosted Storage playback is integrated.

Auth verification follows the existing owner adapter's
[Auth-server verification endpoint](https://supabase.com/docs/guides/auth/jwts#verifying-with-a-shared-secret-signing-key).
No provider secrets, real student records or media are needed for integration tests.
