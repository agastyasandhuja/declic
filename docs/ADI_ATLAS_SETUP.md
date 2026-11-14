# Atlas provisioning handoff — Adi

November 14, 2026. User asked Adi to take the shared cloud database setup while
preserving teammate workflows. **No Atlas project/cluster/user has been created
or verified by this work yet. The user is applying for GitHub Education/student credits and explicitly deferred connecting/provisioning until those are available.**

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
`c84f6d1ec2c2f7c45b1b85b3721d50711c95a5c5`:

- [API status](https://github.com/agastyasandhuja/hackumass-14/blob/c84f6d1ec2c2f7c45b1b85b3721d50711c95a5c5/docs/status/AGASTYA_API.md)
  records a shared runtime, local replica-set tests and ordered migrations; hosted
  Atlas access remains pending. Earlier Adi status saying shared code is absent
  describes Adi's older checkout, not this newer remote branch.
- [Configuration](https://github.com/agastyasandhuja/hackumass-14/blob/c84f6d1ec2c2f7c45b1b85b3721d50711c95a5c5/services/api/app/core/config.py)
  uses `MONGODB_URI`, `MONGODB_DATABASE=hackumass`, and verified TLS in production.
- [Manifest](https://github.com/agastyasandhuja/hackumass-14/blob/c84f6d1ec2c2f7c45b1b85b3721d50711c95a5c5/services/api/pyproject.toml)
  pins PyMongo 4.15.5. Adi's isolated dev lock now matches that pin; existing local
  provider environments are preserved. Do not upgrade the shared lock to 4.17.0.
- [Ordered setup](https://github.com/agastyasandhuja/hackumass-14/blob/c84f6d1ec2c2f7c45b1b85b3721d50711c95a5c5/services/api/app/core/migrate.py)
  applies `001_api_learning_runtime`, optionally `002_video_indexes`. It already
  owns API/video schema assembly; this handoff does not create replacement migrations.
- Core collections are `api_*`. Adi's `app_profiles` and
  `entertainment_catalogs` are separate, so applying the owned drafts does not
  modify core/video collections. Amogh's records remain his schema decision.
- Integration request: move `jsonschema` into shared **runtime** dependencies when
  mounting Adi's verifier/catalog adapters; the inspected manifest currently has
  it only in the development group. Adi does not edit the shared manifest.

## Provisioning target to review

Reuse an existing team Atlas project if available. Otherwise, proposed names are
project `HackUMass 14`, cluster `hackumass14-dev`, database `hackumass`.
Start with an explicitly selected **Free/M0** deployment for the prototype; the
provider/region must be available for that tier and should match the backend
region where practical. Do not silently create a paid tier or consume credits.
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
set was stopped after verification. Hosted checks remain deferred at the user's
request until education/credit access is available.

## Official references checked

- [Free deployment](https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/)
- [Free cluster limitations](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)
- [Atlas database users](https://www.mongodb.com/docs/atlas/security-add-mongodb-users/)
- [Project IP access list](https://www.mongodb.com/docs/atlas/security/ip-access-list/)
- [Validator update permission](https://www.mongodb.com/docs/compass/connect/required-access/)
