# Entertainment collection draft — Adi

manifest.json defines entertainment_catalogs: one atomic bounded private cache
per verified user_id, unique owner index, expires_at TTL index, strict outer
validator and nested video/playback validation derived from the owned v1 schema.
At most 100 items; app normalization deduplicates provider/provider_video_id,
rejects duplicate internal IDs, strips extra provider fields and caps each record
at 32 KiB. Wire timestamps remain zoned ISO strings; cache lifecycle uses BSON dates.

URLs are temporary cached player inputs, never permanent identifiers. Private
batches expire within 24 hours, including provider URLs without known expiry.
Raw media, provider sessions, passwords and unbounded watch history are excluded.
Every read/replacement includes user_id; the phone uses authenticated HTTP only.

Agastya integrates the draft and shared Database/client. Test media from
fixtures/entertainment/feed.json can seed a chosen **synthetic** test user through
CatalogRepository.replace_catalog; no shared/private seed is imported automatically.

## Backfill draft

There were no application records to backfill here. For existing data, audit
owner IDs, duplicate owner documents, >100-item arrays, credential fields, invalid
nested v1 records, insecure URLs and naive timestamps before enabling validators.
Resolve duplicate/ownerless records explicitly; do not merge recommendation data
across users. Reacquire expiring provider URLs rather than treating them as durable
assets. Existing permanent inventories need a separate reviewed migration; this
bounded-cache draft must not replace or delete them. TTL must be added only after
confirming expires_at means cache retention for every existing record.

Regenerate the nested validator after an owned wire-schema edit:

```bash
python3 database/domains/entertainment/generate_validator.py
python3 database/domains/entertainment/generate_validator.py --check
```

The shared wire schema remains authoritative. MongoDB format keywords are
translated/omitted where unsupported; server normalization additionally verifies
zoned timestamps and credential-free HTTPS URLs.
