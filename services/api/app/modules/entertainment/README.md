# Entertainment — Adi

## Adapters

- FixtureCatalog: five public synthetic test-media records; independent of any
  social login, Atlas, Canvas or generation worker.
- SavedCatalog(catalog_path, owner_path): finite local private batch. owner.json
  must contain the exact **verified app subject**, never an email. Missing binding
  fails closed; another user is rejected before reading private catalog data.
- CatalogRepository(database): bounded Atlas-compatible per-user cache,
  replace_catalog(user, items, ttl_seconds=3600), read_items(user).
- CatalogService(repository, cursor_secret, clock?): list_candidates(user,
  cursor=None, limit=5), resolve_playback(video_id, user).
- create_entertainment_router(current_user, catalog): the two existing v1 routes.

All repository callers pass a verified CurrentUser. Mobile never queries MongoDB.
Normalization validates the shared v1 schema and strips unknown provider fields.
Provider credentials, raw responses and media bytes never enter these collections.

Page size 1–20; cursors bind app subject, size and batch revision with HMAC. Batch
replacement gives 409 STALE_CURSOR; invalid/foreign cursors give 422. Expired,
unavailable and embed-only items are excluded, with stable offsets even if expiry
changes between requests. An empty eligible page may still have a next cursor.
Playback returns 410 PLAYBACK_UNAVAILABLE for unavailable/expired records. This
cache **cannot renew Instagram links or fetch new personalized batches** by itself.
A fresh successful provider acquisition must replace the batch. IDs remain stable.

A catalog is one atomic document capped at 100 clips and 32 KiB per record, with
60–86400 second retention and a TTL index. Reads explicitly check expiry because
TTL deletion is asynchronous. A permanent inventory/live provider worker requires
later integration; this design does not claim live recommendation pagination.

## Local API without another teammate's services

Install the isolated dependencies using [auth setup](../auth/README.md). From
repository root, with ignored apps/mobile/.env configured for Supabase Auth:

```bash
PYTHONPATH=services/api .local/adi-dev/venv/bin/python -m uvicorn app.modules.entertainment.experiments.preview_app:create_fixture_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Or set server SUPABASE_URL/SUPABASE_PUBLISHABLE_KEY. This factory verifies real app
authentication and returns **synthetic fixtures**; it is not an accepting fake auth
server. Missing/invalid tokens return 401. The ordinary phone app stays in fixture
mode and does not need this server. The mobile API client requires a reachable
HTTPS origin; localhost on a phone refers to the phone, not this Mac.

For the previously authorized **local simulator** private preview, use the
existing `npm run ios:instagram` guide. Its catalog remains ignored. A separate
`create_preview_app` factory supports owner-scoped local HTTP tests; it is not
started publicly. No owner UUID has been supplied, so private API binding remains
unset. Do not bind by email, guess the UUID or assign the first signed-in caller.

The opt-in Metro GET transport is disabled by default. Public-tunnel delivery of
private catalogs is paused after automatic permission review rejected that data
transfer. Do not enable it until the user approves the specific transfer. It is
not required for teammates to build against fixtures.

See [probe instructions](experiments/README.md), [decision](../../../../../docs/decisions/002-proposed-adi-domain-bootstrap.md)
and [Adi status](../../../../../docs/status/ADI.md) for measured live-vs-fake evidence.

## Live Instagram demo

The owner-bound live adapter is implemented in instagram.py, live.py and
instagram_connection.py. See [exact setup and live acceptance](../../../../../docs/ADI_INSTAGRAM_LIVE.md).
It implements the same domain feed/playback methods and requires the verified
app user on every request. Fresh provider pages replace the finite saved-file
source when the live factory is explicitly selected. Credentials stay in an
ignored owner-only server session file; no password is saved. No automatic login
or checkpoint handling occurs during feed requests.

The existing Atlas snapshot repository and fixture/saved adapters retain their
original behavior. This single-process live demo does not modify Atlas schemas,
shared core/main.py or the shared Python manifest. Agastya registers the router,
maps CatalogFailure, owns lifecycle/hosting and composes any unified-feed reader.
The domain list_candidates(user, cursor, limit) signature differs from core's
EntertainmentReader.list_candidates(user_id, limit); it must not be passed there
without an explicit candidate-model adapter.
