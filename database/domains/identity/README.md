# Identity collection draft — Adi

manifest.json defines app_profiles: one document per Supabase subject, unique
user_id index, strict validator, BSON UTC timestamps, bounded editable display
name, timezone and monotonically increasing revision. MongoDB _id stays internal.
No passwords, access/refresh tokens or duplicated authoritative Auth email are
stored. ProfileRepository derives ownership from verified identity on every query.

Agastya integrates this additive draft into ordered migrations and owns the shared
client/Atlas setup. The installer refuses conflicting existing validators. Real
local MongoDB tests passed; a cloud Atlas deployment has not been configured.

## Backfill draft

No application collection existed in this checkout, so no data migration was run.
For an existing deployment, audit missing/duplicate subjects, timestamp BSON types,
invalid timezone values and absent revisions before enabling strict validation.
Resolve ownership against verified Auth subjects; never infer it from email or
assign orphaned documents to the first caller. Quarantine ambiguous records for
owner review. Initialize a confirmed existing profile revision to 1 and retain
its timestamps; do not silently overwrite names/timezones. Stage validator
changes through the integrator; this draft performs no destructive repair.

Fixture input: fixtures/identity/current-user.json. Its user_demo_01 is synthetic,
not a live Supabase account. Database integration tests use fresh synthetic users.
