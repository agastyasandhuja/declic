# App identity — Adi

Supabase manages passwords/signup/login; this module verifies app bearer tokens
through GET /auth/v1/user over HTTPS, with a 10-second timeout and no redirects.
The returned id is the ownership key. Editable metadata is never authorization.
Auth failures are 401; provider/storage outages are safe retryable 503 errors.

## Public interfaces

- SupabaseVerifier(url, publishable_key).verify_access_token(token) → CurrentUser.
- make_current_user(verifier) → FastAPI dependency; missing/non-Bearer rejected.
- create_identity_router(current_user, profiles=None) → GET /v1/me, PATCH /v1/me.
- ProfileRepository(database) → get_profile(user),
  update_profile(user, expected_revision, changes).

GET returns `{schema_version: "1", ...CurrentUser, revision?}`. If persistence is
configured, absence of a profile means revision 0. PATCH accepts expected_revision
and only display_name/timezone. Updates use an atomic revision predicate. Stale
updates return 409; user_id/role/email changes are rejected. Profile creation is
lazy on first edit; email and Auth account creation time stay authoritative in
Supabase. Call repository functions only with a verified CurrentUser context.

Agastya injects a Database from the shared PyMongo client and registers the router
in core. The module does not create a global database connection or edit main.py.
Core must map AuthFailure and CatalogFailure to the common error envelope with a
request ID and no-store. The local assembly demonstrates this mapping.

## Exact isolated development setup

From repository root, Python 3.13:

```bash
python3 -m venv .local/adi-dev/venv
.local/adi-dev/venv/bin/python -m pip install -r services/api/app/modules/auth/requirements-dev.lock
PYTHONPATH=services/api .local/adi-dev/venv/bin/python -m unittest discover -s services/api/app/modules/auth/tests -p test_auth.py -v
PYTHONPATH=services/api .local/adi-dev/venv/bin/python -m unittest discover -s services/api/app/modules/entertainment/experiments -p 'test_*.py' -v
```

The lock is an **isolated development** environment, including the optional
Instagram probe. Shared manifest/lock integration stays with Agastya. Requested
runtime versions: fastapi 0.162.7, httpx 0.28.1, jsonschema 4.26.0,
pymongo 4.17.0; local runner uvicorn 0.54.0. instagrapi 3.2.12 is optional probe
work, not required for fixture API/profile persistence.

Database tests require a disposable MongoDB server. They never touch the named
application database: each run creates/drops only its new adi_test_<random> DB.

```bash
MONGODB_TEST_URI=mongodb://127.0.0.1:27018 PYTHONPATH=services/api .local/adi-dev/venv/bin/python -m unittest discover -s services/api/app/modules/auth/tests -v
```

Install MongoDB Community from its official platform-specific instructions. On
this Mac, a SHA-256-verified official 8.0.38 ARM64 archive was extracted under
/private/tmp and started manually on 127.0.0.1:27018. This does not install or
provision Atlas. No always-running system service was added.

See [.env.example](.env.example) for placeholders. Configure real values only in
ignored local/deployment secrets. Agastya should assemble owned manifests into
ordered migrations. For a **new disposable development database**, the additive
draft installer can be run explicitly:

```bash
PYTHONPATH=services/api .local/adi-dev/venv/bin/python -m app.modules.auth.database_setup --apply
```

It reads MONGODB_URI/MONGODB_DATABASE from the environment, creates missing
collections/indexes, and refuses a conflicting existing validator. It never drops
data/indexes or silently replaces another stream's schema. Use a migration after
auditing any existing collections; see the owned domain backfill notes.
