# Amogh status

Status: **M1 complete and verified on real UMass Canvas (2026-11-14).**
Live access confirmed with Amogh's own access token in `developer_token` mode.
(Specific course names/IDs are personal data and are not recorded in this file.)

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

## M2 slice + real-time prioritization (2026-11-14, live-verified)

- `canvas/assignments.py`: read-only fetch of the student's assignments with
  their own due dates. Used as M2 ingestion; no writes.
- `curriculum/timing.py`: deterministic, real-time urgency from ACTUAL Canvas
  due dates vs the real current time. Nearest upcoming item, upcoming count,
  urgency score; undated exams reported, never date-guessed.
- `CanvasSourceResolver` now also pulls each course's assignment schedule, so
  courses with no syllabus (the real enrolled courses) become usable; Learning
  Resource Center (LRC) tutoring duplicates are filtered out.
- `run_demo` orders courses by real urgency and tells Gemini the student's
  nearest upcoming work so lessons target it. Verified live: all 4 real courses
  ready, ordered by true deadlines (e.g. Multivariate Calc next due in 2 days);
  Gemini's lessons track upcoming topics (Data Structures -> heaps, matching the
  upcoming "PA11 Heaps" assignment). 19 lessons across the real courses.
- Curriculum owns importance/evidence/timing signals; Agastya owns the final
  runtime feed ranking (consumes these).
- Tests: `test_timing` (8) cover urgency, no-invented-dates, exam detection.

## M4 — Gemini lesson planning (2026-11-14, done + live-verified)

- `planning/planner.py`: a second Gemini call per ready course proposes 2-3
  short (30-60s) lesson objectives; backend assembles contract LessonPlan +
  LessonRequest records with IDs, source refs, evidence/scope status, formats,
  teaching approaches, prerequisites, scope=private.
- Suggested practice is kept separate from confirmed exam coverage; a practice
  item can never carry exam scope. Durations clamped to 30-60; bad enums/formats
  coerced; objectives deduped by meaning within a course.
- Verified LIVE: `run_demo --plan` on real Canvas produced 12 lesson objectives
  across 4 courses. On the synthetic sample syllabus, lessons are fully
  source-grounded (reversal is a separate objective from the intro one).
- Handoff: `handoff.build_profile_ready_event` builds the academics.profile.ready
  payload (profile_id, revision, course_ids, plan_ids). Synthetic plan fixture:
  fixtures/academics/lesson_plan_sample.json. No event bus yet (core pending).
- `python3 -m unittest app.modules.curriculum.tests.test_planning` -> 6 pass.

## M3 — Gemini course profile extraction (2026-11-14, done + live-verified)

- Real Google Gemini integration under `services/api/app/modules/curriculum/`,
  standard library only (REST generateContent, structured JSON output).
- Pipeline: resolve a user's uploaded sources -> send excerpts + source IDs to
  Gemini -> parse -> validate in backend -> assemble a versioned AcademicProfile.
- Gemini returns course units/objectives, assessments with dates + scope,
  textbooks, all citing source IDs. Prompt treats course text as untrusted data.
- Backend validation: drops invented source IDs, coerces bad enums, never
  manufactures an exam time, leaves unknowns null, warns on conflicting dates.
- GEMINI_API_KEY / GEMINI_MODEL / GEMINI_TIMEOUT are server-side only
  (services/api/.env.gemini.local, gitignored). Key is wrapped; never logged.
- Model is configurable; `list_models` CLI discovers Flash ids. Demo verified
  live with `gemini-3.8-flash` (666 prompt + 844 candidate tokens).
- PRIMARY path is live Canvas, not upload: `CanvasSourceResolver` pulls the
  signed-in student's current courses + syllabi via the M1 token and feeds each
  to Gemini. Upload is only the fallback (`run_demo --source upload`).
- Verified LIVE end-to-end on real UMass Canvas (2026-11-14):
  `python3 -m app.modules.curriculum.run_demo` pulled 7 real courses, Gemini
  extracted 4 with syllabi (CICS-210, COMPSCI-250, MATH-233, Intro to C), 3
  without a syllabus marked needs_review. Also verified on the synthetic syllabus
  (Final-exam date left blank for TBA; optional topic flagged not exam scope).
- Model note: `gemini-3.8-flash` was slow (high thinking, minutes/call) and hit
  503 overload. Switched to `gemini-flash-lite-latest` (~1-2s/course); thinking
  level configurable (GEMINI_THINKING_LEVEL, default low). Client retries
  timeouts and 429/503.
- `python3 -m unittest app.modules.curriculum.tests.test_curriculum` -> 16 pass.
- Not done here: M4 lesson planning (next, also Gemini); FastAPI routes (core
  not initialized); Atlas persistence (local JSON stand-in for now); M2 depth
  (modules/files/assignments — most real syllabus bodies are thin); PDF/pptx
  text extraction (upload fallback uses .txt/.md).

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
- `python3 -m app.modules.canvas.validate_access --redact` against real UMass
  Canvas (2026-11-14) → mode `developer_token`, 7 accessible current courses
  listed with syllabus sizes and missing-syllabus flags. **Live M1 pass.**
- Observation for M2: the list includes Learning Resource Center ("LRC … FA26")
  tutoring enrollments that duplicate real courses; M2 must filter these so a
  tutoring section is not ingested as its own course.
- Not run: the OAuth flow against real Canvas (no developer key yet);
  `upload_local` on real files.

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
