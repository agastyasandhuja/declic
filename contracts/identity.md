# Identity contract

Owner: Adi. Shared API dependency assembled by Agastya.

## Identity separation

App account is the primary identity, proposed Supabase Auth. Canvas and social
provider connections are optional external connections, never alternate app user IDs.

CurrentUser internal object:

| Field | Type | Rule |
|---|---|---|
| user_id | string | Verified token subject; immutable internal ownership key |
| email | string or null | Display/contact only, not an authorization key |
| display_name | string or null | User-facing label |
| timezone | string | IANA timezone; explicit default when unknown |
| created_at | timestamp | Account creation |

## API / adapter

- GET /v1/me → schema_version + current user profile.
- PATCH /v1/me → accepted editable profile fields only; cannot change user_id/role.
- Auth service adapter verify_access_token(token) → CurrentUser or auth error.
- Adi provides auth session handling; Agastya exposes core get_current_user to domains.

Signup/login/logout use the managed auth SDK; do not add a second password system
in FastAPI. Mobile uses public configuration only. Backend verification checks
signature, expiry, issuer and audience appropriate to the configured provider.
Never authorize from client-editable user metadata.

## Fixture

Use a synthetic user such as user_demo_01 in fixtures, not a real student's email
or identity. Fixture mode must be explicit and unavailable in deployed production
configuration. Test invalid/expired tokens and cross-user resource requests.

## Owned runtime integration — November 14, 2026

SupabaseVerifier verifies the bearer through the configured Auth server's canonical
get-user endpoint (HTTPS, no redirects, 10-second timeout). Provider failure is 503;
missing/invalid/expired token is 401. Do not treat a caller's email or metadata as
ownership. Agastya assembles the dependency/router in shared core.

GET /v1/me is flat: `{schema_version: "1", user_id, email, display_name, timezone,
created_at, revision?}`. With ProfileRepository configured, revision is 0 for an
unedited profile, then increments on each accepted edit. PATCH /v1/me requires
expected_revision plus one or both display_name (string up to 80 characters or
null) and timezone (valid IANA string). Unknown fields, user_id/role/email edits,
empty changes and invalid timezones return 422. Stale revisions return 409.
Auth email/creation time remain authoritative in Supabase; MongoDB stores only
editable application profile fields and its own update/create timestamps.

Persistence drafts: database/domains/identity. An injected shared Database is the
repository boundary; live Atlas and core assembly remain integration checks.
