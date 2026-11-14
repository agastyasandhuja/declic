# API and adaptive feed handoff

This stream owns `app/core`, `app/workers`, `app/main.py`, `modules/recommendations`,
`modules/quizzes`, the Python manifest/lock, and API-only schema/test artifacts.
It does not implement provider authentication, Canvas/curriculum, entertainment
acquisition, video generation/publication, or mobile UI. Those integrations are
injected through explicit adapters; empty adapters never fabricate real content.

## Composition

Call `create_app(settings=..., identity=..., academics=..., entertainment=...,
videos=..., quiz_reader=..., domain_routers=(...))`. Export that factory from the
integration entry point and start Uvicorn with `--factory`. Do not import another
domain's private repository. Domain routers import `core.dependencies.get_current_user`;
Canvas's OAuth callback instead uses its stored state, as its contract requires.

The factory accepts a `Database` when the caller owns its lifecycle. Otherwise the
API creates/closes its own connection. `database.mongo` is the shared PyMongo
database handle for domain-owned adapters. Atlas must support transactions; run
the explicit migration before startup. Every private domain query still includes
the verified owner, even with a privileged database credential.

For combined API/video persistence, the explicit setup command is
`python -m app.core.migrate --apply --include-videos`: API migration 001 precedes
the video owner's index initialization in migration 002. This prepares storage
only; domain router/reader injection and worker registration remain explicit.

| Owner | Required handoff | Consumer surface |
|---|---|---|
| Adi | Verify signature, issuer, audience and expiry; return `Principal(user_id, timezone)` | `IdentityVerifier.verify_access_token(token)` |
| Adi | Bounded cached normalized clips, no provider headers/cookies | `EntertainmentReader.list_candidates(user_id, limit)` |
| Amogh | Authorized bindings/objectives and date/scope evidence, mapped to `ObjectiveCandidate` | `AcademicReader.list_objectives(user_id)` |
| Video chat | Ready variant summaries, authorization-aware lookup, fresh playback metadata | `VideoReader.list_variants(user_id, objective_ids)`, `get_variant(user_id, video_id)`, `resolve_playback(user_id, video_id)` |
| Video/assessment producer | Validated, scoped MCQ definitions; answers remain backend-only | `QuizReader.list_for_objective(user_id, objective_id)` |

These are consumer projections around the versioned contracts, not renames of
producer service interfaces. Map existing services in an adapter. For example,
Adi's `CurrentUser` becomes `Principal(current.user_id, current.timezone)` after
verification. Supabase credentials/SDK internals stay with the auth owner.

The video service's generation request/status, publication, and video-detail/
playback routes stay with its owner. The owner now provides `FeedVideoReader` in
`app.modules.videos.adapters` and `create_router` in `app.modules.videos.router`.
Compose an owner-configured `VideoService` with
`create_app(videos=FeedVideoReader(video_service),
domain_routers=(create_router(video_service),), ...)`, supplying the other adapters
normally. Playback includes the contract's explicit `expires_at`. Recommendation
code does not reach into the video repository or signer.

`tests/test_video_handoff.py` exercises this composition through authenticated
HTTP requests using the actual video service, adapter, router and local synthetic
repository, plus a fake URL signer. It verifies owner-scoped feed eligibility,
private playback denial before signing, and shared-detail redaction. It does not
generate, upload, or play media. No duplicate generation worker was added here.

## Mobile feed sequence

1. `POST /v1/feed/sessions` with `{}` or `resume_session_id`. Brief reopens reuse
   the session; a scheduled/pending quiz survives idle expiry.
2. `GET /v1/feed?session_id=...&limit=5`. Keep the same limit while following
   `next_cursor`. Retrying a page preserves occurrence IDs and slot accounting.
   Prefetch only a small number of cards. The server caps unconsumed reservations.
3. Send playback events as a JSON array to `POST /v1/feed/events`. Use stable
   event IDs on retry; inspect per-event rejection codes. `visible_watch_ms` is
   cumulative for that occurrence, not the session. `position_ms` is monotonic
   within the occurrence. Playback start/resume establishes a timing anchor and
   cannot add watch time. Report progress before backgrounding; after foregrounding
   send a new playback start using the prior cumulative counters. App lifecycle
   events may omit the payload. Replaying an event never counts twice.
4. A quiz in a prefetched page is not yet pending. When reached, POST its instance
   and occurrence IDs to `/v1/feed/sessions/{id}/quiz-gate`. Lock according to the
   response. No page contains consumable videos after a quiz boundary.
5. Submit `session_id` and `selected_option_id` to
   `/v1/quizzes/{instance_id}/answers` with `Idempotency-Key`. Retry the same key
   and body. A valid wrong answer also unlocks. After the returned revision change,
   discard unseen cached items and fetch without the old cursor.
6. For an actual question/submission failure, use `/recover` with `session_id`,
   `reason` (`content_error` or `submission_unavailable`), and stable
   `client_event_id`. Recovery is ungraded and does not increase mastery.

Public response schemas and the implemented OpenAPI are in
`contracts/schemas/feed`. `/v1/learning/progress` reports unknown mastery as null;
watching alone never increases mastery. No answer key or source reference is in
the quiz card projection. Correctness/explanations appear only after submission.

## Worker and outbox interface

Use `database.run(user_id, operation)` for retryable atomic mutations.
`operation(unit)` may run again after a MongoDB conflict: do database work only,
not provider calls or uploads. `enqueue(unit, owner_user_id=..., job_type=...,
dedupe_key=..., input_ref={...})` can share the transaction with an outbox event.
Keys are unique per owner/type and conflicting inputs return a conflict.

Register handlers using `worker.register(job_type, handler)`. The handler receives
`JobContext(job_id, owner_user_id, input_ref, heartbeat)`. Heartbeat between bounded
stages and before side effects; stop if it returns false. Side effects/publication
must be idempotent and fenced in the domain owner. Expired/cancelled lease tokens
cannot finish a job. Unregistered job types stay queued. Errors persist only a
sanitized code, not provider payloads.

When a wrong answer has no ready alternative teaching approach, the quiz service
enqueues `learning.reteach.requested` with only `objective_id`, `learning_revision`,
and `quiz_instance_id`. The generation integrator must resolve an authorized,
current academic lesson plan before requesting generation. This is a handoff
request; it is not a fabricated `LessonRequest` and is not an active generation
handler until the video/academic owners wire it.

`publish(unit, ...)` persists an internal event with the domain mutation.
`consume_one(unit, consumer, event_type, handler)` persists the consumer receipt
and handler writes in the same transaction. Consumers compare profile revisions
before replacing projections. A worker registrar can dispatch these events into
domain jobs; no public endpoint accepts internal events.

## Runtime limits and verification boundaries

Atlas URI is not configured in this checkout. Local tests cover the real PyMongo
transaction path against a temporary single-node replica set as well as the
explicit SQLite JSON fixture adapter. This does not verify Atlas networking,
cluster credentials, deployment TLS, real Supabase identity, provider playback,
academic import, or iPhone behavior.

The synthetic catalog uses `https://fixture.invalid/...` metadata. It tests
selection and serialization only; those URLs deliberately do not play videos.
Production has no built-in fixture token, no fixture fallback, and no automatic
schema initialization. Secrets stay in environment configuration; TLS verification
cannot be disabled through API settings. Run behind HTTPS with trusted proxy
configuration and infrastructure-level request limits.
