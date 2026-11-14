# Curriculum module

Owner: Amogh. Uses the **Google Gemini API** to turn a student's course material
into a validated, source-referenced academic profile. Contract:
[contracts/academics.md](../../../../../contracts/academics.md).

The primary path uses a bound developer token for local live testing. It reads
syllabi, assignments, modules, Pages, course files and bounded calendar windows
before running Gemini extraction and planning. A private local JSON snapshot
backs development routes and supports manual corrections across reimports.

## Model choice

Use a fast **flash-lite** model (default `gemini-flash-lite-latest`, ~1-2s per
course). Full "thinking" flash models (e.g. `gemini-3.8-flash`) default to high
thinking and took minutes per call plus 503 overload during testing. Thinking
level is configurable via `GEMINI_THINKING_LEVEL` (default `low`).

## Configure

```sh
cp services/api/app/modules/curriculum/.env.example services/api/.env.gemini.local
# edit services/api/.env.gemini.local (gitignored): GEMINI_API_KEY, GEMINI_MODEL
```

The key stays server-side — never in mobile, prompts, logs or commits. A Flash
model is recommended; model names change, so discover yours with `list_models`.

## Commands (run from `services/api`)

```sh
python3 -m app.modules.curriculum.list_models   # Gemini models your key can use
python3 -m app.modules.curriculum.run_demo         # live Canvas -> Gemini -> profile
python3 -m app.modules.curriculum.run_demo --plan  # also M4 Gemini lesson planning
python3 -m app.modules.curriculum.run_demo --source upload --syllabus f.txt --course "Name"
python3 -m unittest app.modules.curriculum.tests.test_curriculum   # synthetic, no network
```

`run_demo` (default) pulls the student's live Canvas courses and syllabi, makes
real Gemini calls, and prints the validated profile. Needs the Canvas token
(.env.canvas.local) and Gemini key (.env.gemini.local). Without a Gemini key it
reports the live call as pending. `--source upload` is the fallback.

## Pipeline

1. `sources.CanvasSourceResolver` — PRIMARY: the student's live Canvas courses
   and course materials as authorized sources. `SourceResolver` is the upload fallback.
2. `prompts/extract.py` — builds the prompt; course text is untrusted data.
3. `client/gemini.GeminiClient.generate_json` — the real Gemini call (JSON out).
4. `validators.validate_extraction` — the trust boundary: drops invented source
   ids, coerces enums, never manufactures an exam time, leaves unknowns null,
   warns on conflicting dates.
5. `extract.build_profile` — assembles and versions the AcademicProfile; one
   failing course does not abort the others. `store.py` persists it.
6. `planning/planner.build_lesson_plans` — M4: a second Gemini call per course
   proposes 30-60s lesson objectives, assembled into contract LessonRequest
   records (suggested practice kept separate from confirmed exam coverage).
7. `handoff.build_profile_ready_event` — the academics.profile.ready payload
   for Agastya. A synthetic handoff plan lives in fixtures/academics/.

## Safety

Gemini receives only text excerpts and authorized source ids — no tokens, no
tools, no URLs, no database. Its output is validated before it is persisted or
handed on. Source resolution is user-scoped. Calendar windows span 180 days on either
side of import. Course file downloads stay on the configured Canvas origin,
are capped at 8 MiB and 12 supported downloads per course, and never follow
cross-origin redirects. UTF-8 text and PPTX slide text are supported. PDF text
extraction uses optional `pypdf` when installed. Unsupported, locked, or
unavailable content is surfaced in `missing_sources`. Scanned PDFs need OCR.

For API composition, construct `AcademicService(storage_dir, gemini_client)` and
one `LocalAcademicJobs()`. Pass both router factories to
`create_app(domain_routers=(...), academics=FeedAcademicReader(service))`. The
Canvas factory also takes server-only `CanvasSettings` and an optional configured
`app_return_url`. These routers use the shared `CurrentUser` dependency from
Agastya's branch. The local job/connection adapters are single-process and
ephemeral. Profile snapshots persist locally. See the academic contract for the
development request bodies and the status handoff for production wiring.

 Structured output shapes the JSON; it does
not establish factual correctness.
