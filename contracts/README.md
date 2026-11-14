# Shared contracts — v1 proposal

These are normative wire/interface proposals for parallel implementation, not
implemented APIs. Runtime JSON schemas, Python models and TypeScript types are
to be added by each domain owner under [schemas](schemas/README.md).

| Contract | Owner | Main consumers |
|---|---|---|
| [identity](identity.md) | Adi | All API domains |
| [entertainment](entertainment.md) | Adi | Feed service and mobile player |
| [academics](academics.md) | Amogh | Video generation and recommendation |
| [learning](learning.md) | Agastya | Curriculum handoff, renderer, mobile |
| [feed](feed.md) | Agastya | Adi's feed UI |

## Common conventions

- API prefix: /v1. JSON field names: snake_case.
- IDs: opaque strings; internal entity IDs UUIDs unless specifically documented.
  External Canvas/provider IDs remain separate strings; do not cast them to JS numbers.
- Every wire document has schema_version: "1".
- Timestamps: ISO 8601 with offset, normally UTC. Course date-only values remain
  YYYY-MM-DD plus IANA timezone and precision; unknown dates are null.
- Ratios/confidence values are 0–1; duration_ms is integer milliseconds;
  duration_seconds is numeric seconds. Never mix these units silently.
- Lists use items and next_cursor; cursors are opaque and bound to user/query.
- Errors use error: {code, message, retryable, request_id, details?}.
  details contains safe validation context, never secrets or private raw documents.
- Protected endpoints use Authorization: Bearer <app access token>.
  Server derives user_id. No consumer may impersonate a user by changing JSON.
- Server returns 401 for invalid authentication, 403 for forbidden operations,
  404 for inaccessible/private resources where revealing existence is undesirable,
  409 for state/version conflicts, 422 for invalid inputs, 429 with Retry-After
  for throttling, and 503 for unavailable dependencies.
- Long-running mutations return 202 with job_id and state, not a held-open render.
- POST requests creating jobs or recording attempts accept Idempotency-Key.
  The server binds the key to user, route and request hash. Conflicting reuse is 409.
- Mutable profile updates carry expected_revision; stale updates return 409.
- Asset IDs are stable; signed playback URLs may expire and be refreshed.

## Internal event envelope

Fields: event_id, schema_version, event_type, occurred_at, actor_user_id,
aggregate_id, aggregate_revision, payload.

Delivery is at least once. Producers persist domain change plus outbox event
atomically. Consumers record processed event IDs and tolerate out-of-order
revisions. A polling job worker is sufficient; no external message broker needed.

| Event | Producer | Payload minimum |
|---|---|---|
| academics.profile.ready | Curriculum | profile_id, revision, course_ids, plan_ids |
| learning.video.ready | Videos | video_id, lesson_request_id, objective_id, scope |
| learning.quiz.answered | Quizzes | attempt_id, objective_ids, correct, learning_revision |

Events carry references, not tokens, raw Canvas files or full private prompts.
Internal events are never accepted directly from untrusted mobile clients.

## Runtime schema ownership

identity and entertainment: Adi. academics: Amogh. learning and feed: Agastya.
Until runtime schemas exist, fixture examples must adhere to these Markdown specs.
Do not assume schemas are enforced merely because this document exists.
