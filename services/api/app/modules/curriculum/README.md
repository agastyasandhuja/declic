# Curriculum module

Owner: Amogh. Uses the **Google Gemini API** to turn a student's course material
into a validated, source-referenced academic profile. Contract:
[contracts/academics.md](../../../../../contracts/academics.md).

Status: **M3 complete and verified live, end-to-end on real UMass Canvas
courses.** The primary path pulls the signed-in student's live courses and
syllabi (via the Canvas token) and sends each to Gemini — no manual upload.
Upload is only a fallback (`--source upload`). Standard library only (REST
`generateContent`). No FastAPI routes yet (core not initialized); persistence
is a local JSON stand-in for the Atlas academics collections.

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
python3 -m app.modules.curriculum.run_demo       # live Canvas -> Gemini -> profile
python3 -m app.modules.curriculum.run_demo --source upload --syllabus f.txt --course "Name"
python3 -m unittest app.modules.curriculum.tests.test_curriculum   # synthetic, no network
```

`run_demo` (default) pulls the student's live Canvas courses and syllabi, makes
real Gemini calls, and prints the validated profile. Needs the Canvas token
(.env.canvas.local) and Gemini key (.env.gemini.local). Without a Gemini key it
reports the live call as pending. `--source upload` is the fallback.

## Pipeline

1. `sources.CanvasSourceResolver` — PRIMARY: the student's live Canvas courses
   and syllabi as authorized sources. `SourceResolver` is the upload fallback.
2. `prompts/extract.py` — builds the prompt; course text is untrusted data.
3. `client/gemini.GeminiClient.generate_json` — the real Gemini call (JSON out).
4. `validators.validate_extraction` — the trust boundary: drops invented source
   ids, coerces enums, never manufactures an exam time, leaves unknowns null,
   warns on conflicting dates.
5. `extract.build_profile` — assembles and versions the AcademicProfile; one
   failing course does not abort the others. `store.py` persists it.

## Safety

Gemini receives only text excerpts and authorized source ids — no tokens, no
tools, no URLs, no database. Its output is validated before it is persisted or
handed on. Everything is user-scoped. Structured output shapes the JSON; it does
not establish factual correctness.
