# Amogh status

Status: M1 code-complete (2026-11-13), tested against synthetic data only.
**Live Canvas access is not yet validated** — needs Amogh's own token or a
developer key. Demo path is ready to light up the moment a token is added.

## Completed

- Branch `amoghs-branch` pushed to origin.
- Canvas config loader with wrapped secrets and single-user token binding.
- Read-only Canvas client: GET only, pinned to institution origin, Link-header
  pagination, 401/403/404 mapping, bounded retry on throttling/5xx.
- `validate_access` script for the own-account token path.
- Upload fallback: validated, hashed, course-labeled private local storage
  producing SourceDocument records marked `provenance.mode = upload, demo = true`.
- `.env.example` with placeholders; real values go in gitignored
  `services/api/.env.canvas.local`.
- Canvas OAuth sign-in helpers (`oauth.py`): authorization URL, single-use
  state bound to the app user, code exchange, token refresh. Untested against
  real Canvas because no developer key exists yet.
- Course preview (`courses.py`): reads the student's own active courses with
  syllabus body, strips HTML for display, records missing syllabus per course
  without failing the others. This is the demo-facing M1 output.
- `--demo` mode and synthetic demo data so the output shape is viewable with
  no token (clearly labelled "not a live sync").

## Research findings (2026-11-13, UMass Amherst)

- Canvas base URL is `https://umamherst.instructure.com`. Checked with
  unauthenticated requests: `/api/v1/courses` returns 401 (API is there),
  `/login` redirects to https://www.umass.edu/it/canvas.
- Students sign in through UMass's Microsoft single sign-on with their NetID
  (`/login/saml` redirects to login.microsoftonline.com). This is the same
  school login used for SPIRE; SPIRE itself is not part of the Canvas login.
- "Log in with your UMass account, then we read your courses" is exactly the
  Canvas OAuth2 flow. It needs a developer key (client id + secret), and on
  hosted Canvas only the school's Canvas admins can issue one. Students cannot
  create one themselves.
- Canvas API policy: apps used by multiple users MUST use OAuth. Asking other
  users to paste a personal access token is a policy violation. A developer
  using their own token for testing is allowed.
- No public UMass Amherst page was found describing how to request a developer
  key or whether students can create personal tokens. Both remain unknown
  until checked in the Canvas account or asked of UMass IT (it@umass.edu).
- Sources: https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth
  and https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth_endpoints

## Commands and verification

Run from `services/api`:

- `python3 -m unittest app.modules.canvas.tests.test_m1 app.modules.canvas.tests.test_oauth app.modules.canvas.tests.test_courses`
  → 29 tests pass (Python 3.14.3). All synthetic; fakes stand in for Canvas.
- `python3 -m app.modules.canvas.validate_access --demo` → prints 3 synthetic
  courses with syllabus previews, clearly labelled synthetic.
- `python3 -m app.modules.canvas.validate_access --redact` with the UMass base
  URL and no token → reports "available modes: upload", exits 1 (expected).
- Not run: any authenticated request to real Canvas; the OAuth flow against
  real Canvas; `upload_local` on real files.

## Interfaces and fixtures delivered

- See [canvas module README](../../services/api/app/modules/canvas/README.md).
- Optional `provenance` object added to upload SourceDocument records
  (additive; to be written into contracts/academics.md with M2 schemas).
- No fixtures yet (M2–M4).

## Dependencies and blockers

- External blocker: UMass-issued Canvas developer key for the OAuth sign-in.
  Must be requested from UMass IT; approval is not guaranteed and may be slow.
- External: whether UMass lets students create a personal access token —
  unknown; Amogh to check https://umamherst.instructure.com/profile/settings
  under "Approved Integrations" for a "+ New Access Token" button.
- Request to Agastya: initialize the Python manifest/FastAPI core so the canvas
  router can be registered; an HTTP client dependency (e.g. httpx) for M2
  concurrent ingestion; shared jobs table handler contract; private storage
  bucket to replace the local `.local/academics` stand-in.
- Request to Adi: current-user shape / test app user ID to bind the demo token to.

## Next actions

- Email UMass IT to request a developer key (redirect URI needed from Agastya's
  API host first).
- Amogh checks for the token button; if present, add it to `.env.canvas.local`,
  run `validate_access --redact`, and record the live result here.
- If token creation is blocked, demonstrate upload mode and record the blocker.
- Then M2: inventory modules, pages, files, assignments, calendar events.
