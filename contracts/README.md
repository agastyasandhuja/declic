# Shared contracts — v1 proposal

November 14 additive entertainment metadata: optional nullable `like_count` and
`comment_count` now pass through the catalog and unified-feed projection. Existing
records remain compatible; provider counts are never fabricated when unavailable.

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

Video runtime update (November 14): internal Storyboard gains optional
`teaching_beats`, required for `guided_v1` generation. Public learning/feed schemas remain
unchanged; see [decision 004](../docs/decisions/004-video-teaching-beats.md).

Reference v2 update (November 14): `space_explainer` joins the learning/feed candidate
formats. Internal Brief gains `presentation` and `trace_kind`; Storyboard gains shots
and public-topic image requests. Reference v2 uses continuous narration with empty
teaching beats. No image/provider credential or renderer path is accepted from mobile.
See [decision 005](../docs/decisions/005-reference-driven-video-templates.md).

Reference v3 update (November 14): internal Brief adds bounded matrix inputs and
`reference_v3`; `math_explainer` joins the learning/feed format enum. Ordinary video
asset delivery remains unchanged. The worker supports music-led matrix lessons and
rendered-frame review; see [decision 006](../docs/decisions/006-video-quality-and-math-template.md).

Semantic motion update (November 14): additive internal Brief fields `math_topic`,
`pythagorean_sides` and `installment_example`, plus `Shot.motion_scene` and enzyme
`space_mode` values, support bounded geometry, payment and decision demonstrations.
Historical matrix/image/space inputs retain their defaults and supported paths.
New plans require the updated worker and renderer together. Public format names,
VideoVariant/feed fields and MP4 delivery remain unchanged; optional mobile display
label **Animated science** does not rename `space_explainer`. See the
[learning contract](learning.md#semantic-motion-extension-november-14) and
[decision 007](../docs/decisions/007-semantic-motion-video-templates.md).


November 14 presentation refinement: narrator captions use the shared white
single-word pop component (sample 22 feedback). This changes renderer style and
recipe identity (4.1.0), not the public format IDs, timestamp fields, caption
payload or feed protocol. Music-led math still has no invented speech captions.
See `services/renderer/ANIMATION_STANDARD.md` for asset reuse and motion review.

November 14 integrated demo: `SessionRequest.refresh_unseen` is an optional
boolean, default false. Mobile cold start uses it to preserve the active-time
ramp while replacing stale unseen reservations; an issued quiz remains required.
`POST /v1/canvas/token` accepts `{token}` and `Idempotency-Key`, verifies the
student's personal token and returns a queued job. Instagram connection routes
accept credentials transiently and store only encrypted provider session state.
See decision 010. Existing provider tokens never appear in response schemas.

November 14 generic visual support: optional internal `Brief.visual_strategy` and
`Shot.semantic_diagram` add bounded comparison, sequence and cause/effect reveals
for abstract topics. Existing visual policies remain the default. Deploy the worker
and semantic-capable renderer together; no public video/feed field changes are
required. See [generic semantic diagrams](learning.md#generic-semantic-diagrams-november-14).

November 14 account-level generic demo: [demo-catalog](demo-catalog.md) defines
opt-in learning settings, four generic courses, 24 reviewed videos/48 quizzes,
atomic ungraded mode switches, and explicit agent-reviewed publication. Feed adds
`playback_seeked` for zero-credit seeks. Entertainment adds bounded owner-connected
read-only Reel comments; no Instagram write operation is exposed.

### Fresh feed bootstrap

`POST /v1/feed/bootstrap` is additive and returns the existing `FeedResponse`.
Mobile uses `limit: 5` and at most six `preferred_video_ids`; hints are
non-authoritative. The server freshly authenticates the owner and preserves
quiz gates, study scheduling and occurrence identities before selecting any
cached starter. Existing wire fields are unchanged. See [feed.md](feed.md).
