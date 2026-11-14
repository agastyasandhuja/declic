# 002 — API core and adaptive feed runtime

Status: implementation in progress. Owner: Agastya, API chat. November 14, 2026.

## Scope and concurrent ownership

This chat edits API core, workers, `main.py`, Python dependency files,
recommendations, quizzes, feed schemas/fixtures, and API-owned migrations/tests.
It does not edit auth, entertainment, Canvas, curriculum, mobile packages, the
videos module, renderer, video-generation schemas, or generation fixtures.
Existing video-design work remains intact. API status is recorded separately in
`docs/status/AGASTYA_API.md`, with an additive link in Agastya's shared status.

## Runtime

Keep FastAPI and use MongoDB Atlas under the accepted storage decision. PyMongo
supplies parameterized document queries and retryable multi-document transactions.
API-owned collections use the `api_` prefix. Never expose database access to the
mobile app. Domain services scope every read/mutation to the authenticated user.
Collection validators/index migrations are an explicit operator action, never an
automatic production HTTP startup operation.

The SQLite JSON-document adapter is an explicit synthetic/test fake only, not a
production database or an emulator proving Atlas behavior. It uses immediate
transactions to exercise persistence and application races locally. The real
MongoDB adapter uses snapshot transactions, majority writes, unique indexes, and
user-state write conflicts to serialize concurrent user sessions. Tests must
separate fake-adapter evidence from live MongoDB/Atlas evidence.

The shared repository adopted Atlas while API work was underway. The initial
SQLAlchemy/PostgreSQL implementation was removed; no application SQL schema or
second production datastore is retained. No extra queue service is introduced.

## Domain handoffs

- Adi supplies token verification and entertainment services. Core provides one
  authentication dependency and router registration. Unconfigured auth fails closed.
- Amogh supplies authorized course bindings and academic context. Recommendations
  consume a small internal candidate projection, not a replacement academic schema.
- The video chat supplies ready catalog projections, playback resolution, quiz
  definitions, and generation handlers. Feed reads never invoke generation.
- Missing variants may enqueue a deduplicated reference-only request through the
  shared job interface. No unregistered handler executes or silently succeeds.
- External/domain adapters must provide cached, bounded snapshots on the feed path.
  Real integrations are not considered verified by passing fake-adapter tests.

## Learning behavior

Use deterministic course → objective → variant selection; the project weights,
ratio ramp, and fairness limits remain configurable heuristics. Quiz correctness
changes learning state, not permission to continue. Atomic attempts, idempotency,
outbox publication, and recommendation revisions share one transaction.

Persist issued feed pages so retries do not consume slot debt or create duplicate
quizzes. Cursors are random opaque database references bound to user, session,
revision, and page size. A reached quiz activates its gate; merely prefetching it
does not lock the current video. Page issuance stops at every quiz boundary.

## Verification requirements

Cover restart durability, concurrent claims and grading, owner isolation,
answer-key exclusion, event replay/plausibility, background time, course fairness,
unknown/date-only assessment evidence, alternate explanations, and stale cursors.
Provider authentication, media playback, and renderer behavior stay explicit
external integration checks owned by their respective streams.
