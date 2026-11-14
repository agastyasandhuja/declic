# Canvas module

Owner: Amogh. Read-only access to a student's Canvas data, plus an upload
fallback. Contract: [contracts/academics.md](../../../../../contracts/academics.md).

Status: Milestone M1 scaffolding. Standard library only (the shared Python
manifest is not initialized yet). No FastAPI routes exist yet. Live Canvas
access has **not** been validated until `validate_access` succeeds against a
real account and that result is recorded in [docs/status/AMOGH.md](../../../../../docs/status/AMOGH.md).

## Connection modes

| Mode | When | State |
|---|---|---|
| `oauth` | School issues a Canvas developer key | Helpers built; untested on real Canvas (no key yet) |
| `developer_token` | Developer's own token, bound to one test app user | Client + check script built |
| `upload` | No Canvas access | Local private store built |

First supported school: UMass Amherst, `https://umamherst.instructure.com`.

## Configure (own-account token)

```sh
cp services/api/app/modules/canvas/.env.example services/api/.env.canvas.local
# edit services/api/.env.canvas.local — it is gitignored (.env.*)
```

The token stays in that file or the backend environment. It is never sent to
mobile, Gemini, logs or fixtures, and `CanvasSettings.developer_token_for`
only releases it for the one bound app user.

## Commands (run from `services/api`)

```sh
python3 -m unittest app.modules.canvas.tests.test_m1 app.modules.canvas.tests.test_oauth app.modules.canvas.tests.test_courses
python3 -m app.modules.canvas.validate_access --demo      # synthetic preview, no token needed
python3 -m app.modules.canvas.validate_access             # live: who am I + active courses
python3 -m app.modules.canvas.validate_access --redact    # counts only, safe to paste
python3 -m app.modules.canvas.upload_local --user-id <app user> --course "<label>" file.pdf
```

Uploads accept .pdf, .pptx, .docx, .txt, .md up to 25 MB and are copied to
`.local/academics/` at the repo root (gitignored).

## Public pieces

- `config.CanvasSettings.from_env(env)` — validated settings, secrets wrapped.
- `client.http.CanvasClient(origin, token)` — `get`, `paginate`; GET only,
  pinned to the institution origin, bounded retries and pages.
  Raises `CanvasAuthError` (401), `CanvasUnavailable` (403/404), `CanvasError`.
- `oauth.build_authorization_url`, `oauth.StateStore`, `oauth.exchange_code`,
  `oauth.refresh_access_token` — school sign-in; the student's password is
  only ever typed into the school's own login page.
- `courses.summarize_current_courses(client)` — the student's own current
  courses with a syllabus preview and per-course missing-source notes.
- `ingestion.uploads.store_upload(...)` — returns `(SourceDocument, created)`.
