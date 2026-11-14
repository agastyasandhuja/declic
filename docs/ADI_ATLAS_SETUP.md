# Atlas provisioning handoff — Adi

November 14, 2026. **Hosted Atlas initialization is verified.** The user created
a Free/M0 cluster and saved the database credential locally. The application
database is `hackumass`. Adi's two domain drafts and Agastya's existing shared
API/video migrations are applied. TLS connection, transaction commit/rollback,
validator/index metadata and shared job constraints passed hosted checks.

This establishes the database foundation. It does not establish deployed API
hosting, real account-to-API integration, academic persistence, Storage signing
or physical-iPhone acceptance.

## Hosted result — November 14, 2026

- First successful user-run read-only check: `2026-11-14T16:20:16.699698+00:00`.
- Applied the existing Adi installer: app_profiles and entertainment_catalogs;
  validators/indexes match, strict error enforcement enabled.
- Used Agastya's published source snapshot
  `36fbc201228cfad0055cc895b4d8af02930c509f`, without merging or modifying it.
  Verified migration/config/database/collection/video-repository blobs against
  their Git object hashes before execution. A read-only guard found a fresh
  shared namespace, so existing shared schemas were not overwritten.
- Executed the owner's `apply_ordered(database, include_videos=True)`: migration
  `001_api_learning_runtime` creates 12 API collections; `002_video_indexes`
  initializes 3 video collections. Both migration markers are now present.
  Core validator/index definitions and video indexes match the published source.
  The core startup migration check passes. Adi schemas stayed unchanged and
  unrelated collections were preserved. No teammate implementation was edited.
- Final hosted preflight: `2026-11-14T16:30:48.734149+00:00`; connection, replica
  set/sessions, both owned schemas/indexes, both core migration markers and
  transaction commit/rollback/cleanup all passed. The temporary probe was removed.
- Separate hosted job checks: invalid api_jobs documents were rejected (121),
  duplicate owner/job-type/dedupe-key records were rejected (11000), and all
  synthetic job inserts were aborted. No synthetic jobs remain or were queued.
- Bootstrap wrappers/reports remain ignored under .local/atlas-readiness. Only
  safe results are recorded here; no URI, username, password or provider data is
  committed. services/api/.env remains ignored with mode 0600.

### Remaining access and integration handoff

The currently saved credential has a broad database role (observed, not guessed).
A dedicated runtime database user with readWrite scoped to hackumass still needs
to be configured before deploying the API; bootstrap credentials are not the
intended runtime identity. No database-user grants or project IP rules were
changed by the agent. Current workstation connectivity works; deployed backend
network access must be configured for the actual host.

Agastya retains runtime/migration assembly and real adapter/router integration.
Amogh's published branch still uses local academic JSON persistence; his Atlas
repository/collection definitions remain his work. No academic schemas were
invented, no Canvas/Gemini requests were made and no private source data was
uploaded. Supabase private Storage setup remains separate.

## Work split

| Work | Owner for this handoff |
|---|---|
| Atlas account/project selection, cluster provisioning, database access and network configuration, cloud connectivity check | Adi, per current user direction |
| Shared MongoDB runtime/client lifetime, Python manifest/lock and ordered migrations | Agastya |
| Identity/entertainment collection drafts and repositories | Adi |
| Academics collection drafts/readers | Amogh |
| Learning/jobs/feed/quiz/video persistence and transaction semantics | Agastya |

No teammate messages have been sent. This is a documented proposed handoff, not
confirmation that another teammate has received or agreed to a changed task.
Existing runtime implementations and contracts remain with their owners.

## Current remote compatibility evidence

Inspected Agastya's published feature branch at
`36fbc201228cfad0055cc895b4d8af02930c509f`:

- [API status](https://github.com/agastyasandhuja/hackumass-14/blob/36fbc201228cfad0055cc895b4d8af02930c509f/docs/status/AGASTYA_API.md)
  records a shared runtime, local replica-set tests and ordered migrations. The
  hosted checks above extend that published checkpoint. Earlier Adi status saying
  shared code is absent describes Adi's older checkout, not this remote branch.
- [Configuration](https://github.com/agastyasandhuja/hackumass-14/blob/36fbc201228cfad0055cc895b4d8af02930c509f/services/api/app/core/config.py)
  uses `MONGODB_URI`, `MONGODB_DATABASE=hackumass`, and verified TLS in production.
- [Manifest](https://github.com/agastyasandhuja/hackumass-14/blob/36fbc201228cfad0055cc895b4d8af02930c509f/services/api/pyproject.toml)
  pins PyMongo 4.15.5. Adi's isolated dev lock now matches that pin; existing local
  provider environments are preserved. Do not upgrade the shared lock to 4.17.0.
- [Ordered setup](https://github.com/agastyasandhuja/hackumass-14/blob/36fbc201228cfad0055cc895b4d8af02930c509f/services/api/app/core/migrate.py)
  applies `001_api_learning_runtime`, optionally `002_video_indexes`. It already
  owns API/video schema assembly; this handoff does not create replacement migrations.
- Core collections are `api_*`. Adi's `app_profiles` and
  `entertainment_catalogs` are separate, so applying the owned drafts does not
  modify core/video collections. Amogh's records remain his schema decision.
- Integration request: move `jsonschema` into shared **runtime** dependencies when
  mounting Adi's verifier/catalog adapters; the inspected manifest currently has
  it only in the development group. Adi does not edit the shared manifest.

## Provisioning choices and access review

The user selected **Free/M0** and cluster `hackumass14`; the initialized application
database is `hackumass`. For future provisioning, the provider/region must support
the chosen tier and should match the backend region where practical. No paid tier
or credits were configured by the agent.
Any later upgrade is a separate cost decision. No sample dataset is needed.

Proposed database identities, restricted to this database/cluster:

| Principal | Database roles | Purpose |
|---|---|---|
| `hackumass_app` | `readWrite` on `hackumass` | API/worker runtime |
| `hackumass_migrate` | `readWrite` + `dbAdmin` on `hackumass` | Explicit migration execution |

The migration principal needs `dbAdmin` because Agastya's existing setup uses
`collMod` to update validators. The runtime should not receive that role. Avoid
broad any-database/admin grants. Database credentials differ from Atlas dashboard
login; keep passwords/URIs in local or deployment secrets, never Git/mobile/chat.
The final project, cluster, database roles and network rules should be visible for
review before those access grants are applied.

For development, allow the current workstation's exact public IP (`/32`) with a
suitable expiration. Add deployed backend egress addresses once the host exists.
Do not replace the access list or add `0.0.0.0/0`. A network rule is not a substitute
for TLS, database authentication or app-user ownership checks.

## Exact configuration and hosted checks

Shared names remain unchanged. Adi's .env.example now uses the actual shared
`hackumass` default; this changes a placeholder, not an existing database.

Use ignored local files, for example:

- `services/api/.env`: runtime URI and `MONGODB_DATABASE=hackumass` for Agastya's
  service commands run from services/api.
- `.local/atlas-readiness/.env.migrate`: migration URI and the same database name.

The preflight helper reads only MongoDB variables from `--env-file`; process
variables take priority. It does not source or execute the file, read provider
keys, or print the URI/password. Atlas SRV/TLS is required; loopback is allowed
only with the explicit local-test flag.

From repository root, the lightweight preflight needs only the driver's pinned
version (the same one used by Agastya):

```bash
python3 -m venv .local/atlas-readiness/venv
.local/atlas-readiness/venv/bin/python -m pip install 'pymongo==4.15.5'
```

Use that environment, or the shared locked environment after integration:

```bash
PYTHONPATH=services/api .local/atlas-readiness/venv/bin/python -m app.modules.auth.atlas_preflight --env-file services/api/.env
```

Default checks are **read-only**: ping, replica-set/session capability, owned
validator/index presence, and the existing core migration markers. Report status
`completed` means the check ran, not that all application integrations are ready;
inspect the individual booleans. A new cluster can be connected while every
migration marker is still false.

Apply only Adi's additive drafts, and verify committed/aborted transactions with
synthetic records, when ready to initialize that selected database:

```bash
PYTHONPATH=services/api .local/atlas-readiness/venv/bin/python -m app.modules.auth.atlas_preflight --env-file .local/atlas-readiness/.env.migrate --apply-owned-drafts --write-test
```

`--apply-owned-drafts` delegates to the existing Adi installer: it creates missing
owned collections/indexes and refuses a conflicting existing validator. It does
not touch `api_*`, academic or video collections. `--write-test` creates one fresh
`_adi_atlas_probe_<random>` collection, verifies majority commit and snapshot
rollback, then drops that exact test collection. It never drops an application
database or reads course/user documents. A failed cleanup is reported with the
nonsecret probe name. Interrupted checks may leave a probe for later cleanup.

The report defaults to ignored `.local/atlas-readiness/report.json`, mode 0600;
it contains statuses/booleans only, not credentials or raw driver errors. It is
not a deployment secret store. DNS/network/auth/permission failures are distinct
safe outcomes. A local result must never be presented as cloud verification.

Agastya runs his existing ordered command in his integrated runtime, using the
migration environment, then restores runtime credentials for serving traffic:

```bash
python -m app.core.migrate --apply --include-videos
```

Adi will not transplant, renumber or rewrite this command on an older checkout.
Core should inject its `Database.mongo` (the PyMongo Database) into Adi's repositories,
not the `app.core.database.Database` wrapper. It needs the Adi/Amogh adapter imports
wired before real authenticated feed
integration; provisioning alone does not establish that route composition.

## Verification performed in this preparation

An isolated environment at `.local/atlas-readiness/venv` uses PyMongo **4.15.5**.
A temporary MongoDB **8.0.38** replica set binds only `127.0.0.1:27028` and uses
synthetic `/private/tmp` data. The tests create/drop only their fresh `adi_test_*`
databases. This is not the cloud project and requires no team credentials.

```bash
MONGODB_TEST_URI='mongodb://127.0.0.1:27028/?replicaSet=adi_atlas_preflight' PYTHONPATH=services/api .local/atlas-readiness/venv/bin/python -m unittest discover -s services/api/app/modules/auth/tests -v
```

Initial run: **12/12 passed** (three auth checks, five existing real MongoDB
repository/HTTP checks, three preflight configuration/redaction checks and one
real replica-set preflight test). The new preflight test proves read-only checks
do not create collections, transaction commit/rollback/cleanup work, and an
unrelated synthetic collection remains intact. Final run: **13/13 passed**, also including the full CLI and an existing
warn-only validation policy that initialization refuses to overwrite. CLI --help,
pip check and the owned wire-validator drift check passed. The temporary replica
set was stopped after verification. These were the preparation checks; hosted
results are now recorded above after the user proceeded with Free/M0.

## Official references checked

- [Free deployment](https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/)
- [Free cluster limitations](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)
- [Atlas database users](https://www.mongodb.com/docs/atlas/security-add-mongodb-users/)
- [Project IP access list](https://www.mongodb.com/docs/atlas/security/ip-access-list/)
- [Validator update permission](https://www.mongodb.com/docs/compass/connect/required-access/)


## Authentication diagnostic follow-up

Atlas can wrap authentication and permission errors in server code 8000. The
preflight now distinguishes known authentication phrases (AUTH_FAILED) from
permission phrases (ACCESS_DENIED), keeping all raw messages/credentials private.
The first hosted check reached Atlas but authentication was rejected before any
schema work; missing migrations could not explain that failure. The user
subsequently corrected the credential locally. Hosted authentication and setup
now pass as recorded above.
