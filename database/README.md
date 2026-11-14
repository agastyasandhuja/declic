# MongoDB Atlas ownership and setup plan

MongoDB Atlas is the application database, replacing the scaffold's proposed
Postgres application tables. Supabase Auth manages accounts; Supabase Storage
holds original course files and generated media. This decision does not replace
Supabase's internal Postgres infrastructure for its managed services.

See the [accepted decision](../docs/decisions/001-proposed-atlas-application-data.md).
API collection validators and executable setup are implemented and tested against
a local MongoDB replica set. Adi recorded hosted Atlas initialization in [the setup handoff](../docs/ADI_ATLAS_SETUP.md).
The integrated checkout requires its own configured credentials and connection check. See [API verification](../docs/status/AGASTYA_API.md).

Domain drafts:

- domains/identity and domains/entertainment — Adi.
- domains/academics — Amogh.
- domains/learning — Agastya.

Agastya owns the shared Atlas connection lifecycle, Python driver/dependencies,
database configuration, and ordered change assembly under migrations. Each owner
drafts their collection validators, indexes and data backfills under their domain.
Record dependencies and use additive changes rather than editing one shared schema.

The existing migrations directory remains the home for ordered, repeatable MongoDB
database changes. No SQL application schema is planned. Supabase Storage access
policies are configured separately. Earlier task-guide references to a jobs table
mean the Atlas jobs collection under the adopted decision.

## Available ordered setup

From `services/api`, using the isolated API environment and configured MongoDB:

```sh
uv run --locked python -m app.core.migrate --apply
uv run --locked python -m app.core.migrate --apply --include-videos
```

The first command applies `001_api_learning.py`: API-owned validators and indexes.
The second applies 001 followed by `002_video_indexes.py`, which delegates to the
video owner's public repository initializer. It does not duplicate the owner's
index definitions or add validators the owner has not provided. Both commands are
explicit operator actions, separate from HTTP startup. Success markers appear
only after each migration finishes; index operations can partially succeed before
a failure. Rerun after explicitly resolving any conflicting existing records.
No migration deletes data or initializes the identity/entertainment/academic domains.

## Data boundaries

- Atlas: application profiles, entertainment metadata, academic sources/profiles/
  plans, video metadata, jobs/outbox events, quizzes, mastery and feed state.
- Private Supabase Storage buckets: syllabus PDFs, slides, source snapshots,
  narration, captions, thumbnails and generated MP4s. Atlas holds stable asset IDs
  and storage references; signed URLs are temporary responses, not identifiers.
- Deployment secrets: Atlas URI, provider credentials and token-encryption key.
  Per-user Canvas tokens remain encrypted server-only connection records.
- Keep Supabase Auth's verified subject as the contract user_id. MongoDB _id is an
  internal implementation detail; v1 field names and string IDs do not change.

## Shared setup handoff to Agastya

1. Provision an Atlas cluster and application database; configure permitted backend
   network access and a database user restricted to the application database.
2. Add server-only MONGODB_URI and MONGODB_DATABASE configuration and placeholder
   examples when initializing the backend. Never use EXPO_PUBLIC for Atlas secrets.
3. Select and pin the Python driver in the shared manifest/lockfile, then expose
   one shared connection lifecycle to domain persistence adapters.
4. Assemble domain validators and indexes. Enforce unique generation keys,
   effective quiz submissions, event IDs and scoped idempotency keys in storage.
5. Implement atomic job claims with leases/retries. Use transactions for changes
   that must commit with outbox events or related quiz/learning/feed state.
6. Test cross-user rejection, duplicate submissions/enqueues, interrupted workers,
   and repeatable database setup before claiming the integration works.

Storage uploads and Atlas transactions cannot commit together. Upload first,
validate, then publish ready metadata; retries and orphan cleanup must be explicit.

## Access control

All Atlas access is server-side. Every private query checks ownership derived from
the verified app access token. Supabase row-level security does not protect Atlas
collections, and database credentials must never reach the mobile app or renderer.

Keep answer keys and credentials out of client responses. Authorize private file
access in the backend before issuing short-lived signed URLs; keep general client
reads/writes to private buckets disabled unless explicitly scoped by policy.
Only synthetic seed data belongs in seeds; no real Canvas exports.


## Integrated identity and entertainment setup

`uv run --locked python -m app.core.migrate --apply --include-videos --include-identity-catalog`
adds ordered step `003_identity_entertainment`, delegating to Adi's existing
`apply_domain_drafts(Database.mongo)`. This step requires 001; video step 002 is
independently optional. It creates missing schemas/indexes, refuses conflicting
existing validators, and writes its success marker only after setup succeeds.
Already-applied Adi schemas are safe to rerun. API startup never applies migrations.

The configured HTTP factory is `app.runtime:create_app`; it checks both core
migration readiness and actual owned identity/catalog validators/indexes. This
accepts Adi's previously installed schemas without requiring a new marker just
to start the API. Academics still has no Atlas schema/repository in the merged
branch and is not initialized by this command.
