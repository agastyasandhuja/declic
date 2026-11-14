# Atlas application data with Supabase Auth and Storage

Status: accepted by the user in the active conversation; implementation pending.
Date: November 13, 2026, America/New_York.
Proposer: Adi workstream.
Affected owners: Adi, Amogh, Agastya (shared backend/data integration).

## Problem

The repository initially proposed Supabase Auth, Postgres, and Storage, but has no runnable
implementation or provisioned infrastructure. Before implementing Adi's mobile
milestone, clarify where imported Canvas material, structured course profiles,
generated assets, feed state, and generation jobs belong. MongoDB Atlas credits
and a hackathon prize make a substantive Atlas implementation worth considering.

## Decision

Keep Expo + React Native + TypeScript for the phone, Supabase Auth for app
identity, FastAPI for the modular backend, and Remotion/FFmpeg for rendering.
Use MongoDB Atlas as the application database, Supabase Storage for file bytes,
with existing background-worker boundaries. Render remains the proposed host for
the public API and trusted background orchestration workers.
Amogh's Gemini workflow and Agastya's generation provider choices stay theirs.

The user approved replacing the proposed Postgres application datastore with
Atlas, then requested updating existing files and committing directly to main.
This accepts the database boundary; it does not establish working infrastructure
or authorize editing another owner's implementation. No resources are provisioned
by this documentation change. The existing filename is retained for stable links.

## Data placement

| Data | Authoritative location | Owner / access |
|---|---|---|
| App accounts, passwords, auth sessions | Supabase Auth | Adi; managed SDK, no second password store |
| Mobile session credentials | Secure device storage | Adi; clear app-private state on logout |
| App profile preferences | Atlas identity collection | Adi; use verified Supabase subject as user_id |
| Entertainment catalog and playback asset references | Atlas entertainment collections | Adi; approved catalog, no social secrets in responses |
| Course memberships and source metadata | Atlas academics collections | Amogh; user-scoped |
| Original syllabus PDFs, slides, sanitized HTML snapshots | Private Supabase Storage bucket | Amogh; immutable paths, authorized access |
| Extracted text chunks and source locators | Atlas academics collections | Amogh; private, bounded records |
| Versioned profiles, evidence, corrections and lesson plans | Atlas academics collections | Amogh; existing academic wire contracts |
| Generic objectives and approved reusable video metadata | Atlas domain collections | Matching domain owner; generic content only |
| Narration, captions, thumbnails and MP4 bytes | Supabase Storage | Agastya; private until explicitly approved generic |
| Jobs, outbox events, video generation state | Atlas learning/core collections | Agastya; leases, retries, idempotency |
| Quiz definitions/answers, attempts, mastery, feed sessions/events | Atlas learning collections | Agastya; answers server-only, private state user-scoped |
| Static provider keys, token-encryption key, database URI | Backend deployment secrets | Matching owner; never mobile or renderer |
| Per-user Canvas OAuth tokens | Encrypted server-only connection records | Amogh; encryption key outside Atlas |

Supabase's internal Postgres remains part of its managed Auth/Storage services.
Do not also maintain business records in Postgres: application data has one
authoritative database. Atlas stores stable asset IDs and bucket/object paths,
not permanent signed playback URLs. Raw file bytes stay in object storage.

Keep separate records for sources, profile revisions, bindings, requests, and
assets. Do not embed every course, all source text, or an unbounded event history
inside one user document. Preserve the existing normalized external interfaces;
physical collections need not mirror a single API response.

## Ingestion and publication flow

1. FastAPI verifies the app access token and derives user_id from its subject.
2. Amogh inventories all accessible current Canvas courses using read-only access.
   Inspect syllabus HTML and permitted syllabus/module/file references; do not
   assume every course has one syllabus PDF. Keep missing-source states explicit
   and provide the existing upload fallback.
3. Store authorized source bytes privately and index their provenance in Atlas:
   source/course/owner IDs, hashes, source revision, fetched time, resource type,
   and storage reference. Reuse unchanged content within the authorized scope.
4. Amogh publishes validated profile/plan revisions, evidence, and manual
   corrections. Preserve date-only precision and source timezones.
5. Persist a domain change plus its outbox event in one Atlas transaction. Agastya
   consumes plan references idempotently and enqueues bounded generation jobs.
6. Workers reuse a compatible ready asset or generate a new variant. Enforce a
   unique generation key including owner scope; claim jobs atomically with leases.
7. Trusted orchestration stages local inputs for an isolated renderer. Generated
   code receives no application/provider credentials, no network egress, and
   bounded CPU, memory, and execution time. A private Render service alone does
   not establish those isolation properties; Agastya must choose and test the
   sandbox execution host before executing generated code.
8. Upload completed outputs, verify them, and then atomically publish ready
   metadata plus the corresponding event in Atlas. Storage upload and database
   commit cannot share a transaction: failed publication needs idempotent retries
   and cleanup of orphaned objects. Never select a partial asset for the feed.
9. Agastya selects ready authorized videos with deterministic ranking and diversity
   rules. Adi plays them; importing and rendering never block a feed request.

## Authorization and consistency

- The phone calls Supabase Auth and the authenticated FastAPI API. It does not
  connect to Atlas, receive database credentials, or query private collections.
- Every private Atlas query includes ownership derived from verified app identity.
  Supabase RLS does not protect Atlas collections.
- For files whose authorization lives in Atlas, FastAPI checks access before
  issuing a short-lived signed URL. Keep private buckets inaccessible to general
  client reads/writes; any direct upload grant is scoped to an authorized path.
- Keep private course bindings and evidence separate from generic lessons. A
  matching title or vector similarity does not approve reuse or publication.
- Use unique indexes for generation keys, effective quiz submissions, consumed
  event IDs, and idempotency keys. Transactions coordinate quiz outcomes, mastery,
  recommendation revision, and outbox state where multiple records must agree.
- A job heartbeat/lease and bounded retries make recovery explicit. No Redis or
  external message broker is proposed for the initial demo.

## Meaningful Atlas demonstration

Atlas will hold the actual course-to-lesson records and runtime application
state. A possible second milestone is semantic discovery of reusable generic
lessons: match differently worded objectives to candidate lessons, then check
level, language, notation, version, readiness, and access scope deterministically.
Atlas Vector Search supports metadata filters; those filters and server-side
authorization must prevent private cross-user retrieval.

Embeddings, indexes, retrieval quality, and cluster capability require separate
implementation and tests. Exact canonical-key matching is the first fallback.
Neither vector search nor a trained recommendation model is required for Adi's
first mobile milestone.

## Integration impact and ownership

- No v1 route, ID, field name, or public service signature needs to change merely
  because persistence changes. MongoDB _id values stay internal; retain contract
  string IDs and timestamp/date semantics.
- Agastya owns Atlas connection setup, shared Python dependencies, collection/index
  initialization, transactions/outbox infrastructure, job dispatch and deployment.
  SQL application migration plans are replaced by ordered MongoDB collection,
  validator, index and backfill changes under database/migrations; Supabase Storage
  policies still require their own configuration.
- Amogh owns academic collection definitions and persistence adapters. Coordinate
  with that stream before changing its storage implementation.
- Adi owns identity/entertainment persistence adapters and mobile integration.
  The first milestone can use fixtures and Supabase Auth without waiting for Atlas.
- Domain owners provide schema/index drafts; Agastya integrates shared setup.
  Shared architecture/database instructions reflect the user-approved decision.
- Amogh and Agastya have not been contacted. Their implementation tasks are
  documented as handoffs; no changes to their implementation or contracts are
  part of this documentation update.

## Alternatives and tradeoffs

1. **Supabase Auth + Postgres + Storage:** fewest platforms and matches the scaffold.
   Postgres JSONB can store evolving academic documents, so Atlas is not required
   solely because Gemini emits JSON. Prefer this if the team already has working
   Postgres integration or minimizing setup outweighs the Atlas opportunity.
2. **Atlas for academics, Postgres for runtime state:** feasible, but splits the
   lesson-plan/job handoff across databases and introduces reconciliation work.
   Not recommended for this hackathon unless existing implementations justify it.
3. **Atlas application database + Supabase Auth/Storage (accepted):** substantive
   Atlas use without replacing managed authentication or building media storage.
   Costs include an extra provider, explicit backend ownership enforcement,
   application-managed relationships, and collection/index/transaction setup.

Render is the proposed host because this architecture needs an HTTPS Python API
and persistent background processes. Keep those deployed from the same backend
codebase. Render worker support is documented, but resource sizing, renderer
sandbox support, codec compatibility, database connectivity and actual throughput
remain untested. No hosting price or free-tier capacity is assumed here.

## Rollout

1. Use this accepted record and the updated database/integration guides as the
   persistence handoff to Amogh and Agastya.
2. Adi creates the Expo workspace, auth/session adapter, authenticated API client,
   fixture catalog, player lifecycle and setup documentation in a dedicated branch.
3. Agastya provisions shared backend data/worker configuration; domain owners add
   validators/index drafts and fake-compatible persistence interfaces.
4. Test authenticated ownership, interrupted jobs, duplicate events/quiz answers,
   and file-access boundaries before integrating real private course material.
5. Integrate one course-to-video path, then multiple courses and adaptive ranking.

Use small commits for workspace setup, auth/API client, playback/recovery, and
documentation/verification. Preserve other streams' work and do not commit secrets,
raw Canvas exports, downloaded entertainment, or generated MP4s.

The current change updates documentation only and commits to main at the user's
explicit request. It does not initialize the mobile app or runtime database code.

## References checked

Documentation research only; no provider or device integration was tested.

- [Expo video](https://docs.expo.dev/versions/latest/sdk/video/)
- [Expo SecureStore](https://docs.expo.dev/versions/latest/sdk/securestore/)
- [Supabase React Native Auth](https://supabase.com/docs/guides/auth/quickstarts/react-native)
- [Supabase private/public buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals)
- [Supabase JSONB alternative](https://supabase.com/docs/guides/database/json)
- [Canvas courses and syllabus HTML](https://developerdocs.instructure.com/services/canvas/resources/courses)
- [MongoDB data modeling](https://www.mongodb.com/docs/manual/data-modeling/)
- [MongoDB transactions](https://www.mongodb.com/docs/manual/core/transactions/)
- [MongoDB findOneAndUpdate](https://www.mongodb.com/docs/manual/reference/method/db.collection.findoneandupdate/)
- [MongoDB Vector Search query filters](https://www.mongodb.com/docs/vector-search/query/aggregation-stages/vector-search-stage/)
- [Render background workers](https://render.com/docs/background-workers)
