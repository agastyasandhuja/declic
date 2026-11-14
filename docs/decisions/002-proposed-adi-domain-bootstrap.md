# Adi domain bootstrap and bounded entertainment cache

Status: proposed shared integration; implemented and locally tested inside Adi's
owned modules only. November 14, 2026. Atlas remains the accepted application DB.

## Scope and integration impact

The shared API/core and its dependency manifest remain Agastya's responsibility.
Adi exports router factories and repositories accepting an injected PyMongo
Database. A local experiment factory assembles only identity/entertainment for
independent tests. It is not a second deployed API or replacement for main.py.
Agastya should register these factories and the common safe error handlers.

Supabase's canonical authenticated get-user endpoint verifies app tokens remotely.
Its verified id is the ownership subject; metadata/email/query IDs cannot choose
an owner. A dependency outage returns retryable 503, rather than an auth success
or guessed identity. The mobile session stays intact on transient refresh errors.

Identity stores a small profile in app_profiles. Entertainment initially stores
one bounded private batch per user in entertainment_catalogs: at most 100 records,
32 KiB per normalized record, atomic replacement, maximum 24-hour retention. This
avoids transactions for a finite cache and prevents mixed-version pagination.
It is not a permanent provider asset inventory or a recommendation engine.
Signed media URLs are temporary cache fields; stable video/asset IDs remain the
contract identity. Provider sessions and media bytes are excluded. Expiry is
checked before access, independently of eventual TTL deletion.

HMAC cursors bind subject, page size and batch revision. Changed batches return
409 STALE_CURSOR. Agastya supplies the same server-only 32-byte signing key to all
replicas. A temporary random process key is allowed only for the local preview;
restarting it invalidates outstanding cursors. No shared field/route is renamed.
GET /v1/me adds optional revision; PATCH uses existing expected_revision semantics.

An opt-in Metro transport forwards only GETs for these three domain routes to
fixed loopback port 8000. It strips cookies, rejects redirects and bounds transfer.
It is disabled by default and excluded from exports. Enabling private catalogs
through a public Expo tunnel remains paused and requires the user's specific
approval; tests use synthetic loopback services only.

## Assembly handoff

- Integrate database/domains/{identity,entertainment}/manifest.json in ordered
  migrations. Do not drop/tighten existing collections without an audit/backfill.
- Inject one shared Database into ProfileRepository and CatalogRepository; use
  sync routes (FastAPI thread pool) or otherwise avoid blocking the event loop.
- Add pinned Python dependencies and shared client lifetime/timeouts in core.
- Configure Atlas access, API hosting and private object Storage policies in their
  existing ownership streams. No cluster, public endpoint or bucket is provisioned.
- A larger/live inventory should use separate stable asset records and scoped
  bindings once its owner agrees; do not silently expand this bounded cache.

## Validation

Real local MongoDB 8.0.38 tests validate owned indexes, validators, profile CAS,
private queries, atomic batch replacement, expiry and cursor scope. ASGI HTTP tests
use a fake Supabase transport; they are not successful live-account API tests.
Neither test class establishes live Atlas connectivity, cloud transactions or
private Storage authorization.
