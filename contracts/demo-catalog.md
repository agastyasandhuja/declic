# Shared generic demo catalog and learning mode

The demo is opt-in per authenticated app account. Atlas `api_user_state.demo_mode`
defaults to false when absent. No Canvas connection or private topic binding is
copied, shared, or rewritten by this setting.

- `GET /v1/learning/settings` → `{schema_version: "1", demo_mode: boolean}`.
- `PATCH /v1/learning/settings` accepts exactly `{demo_mode: boolean}` and returns
  the same fields plus `recommendation_revision` (maximum affected session revision,
  or null if no session was changed). Repeating the current value is a no-op.
- `GET /v1/learning/demo-catalog` returns `{schema_version: "1", revision, courses}`.
  Each course contains `course_id`, `title`, `objectives: [{objective_id, title}]`,
  and `video_count`. An unpublished catalog has revision 0 and empty courses.
  Quiz answers, internal Storage keys and review records never appear here.

All routes require app authentication. No body accepts a user ID. After changing
mode, mobile discards every locally issued card/gate and resumes/refetches the feed.
The server atomically invalidates old cursors, rejects even previously started
old-curriculum playback events, and recovers pending/issued quizzes **ungraded**.
Existing graded attempts and learning state remain unchanged. Each curriculum has
separate objective IDs, so prior private learning cannot become generic mastery.

The integrated demo projects the reviewed registry down to four lessons:
CS 210 Tax Bill / Undo Stacks, CS 220 Promise States, ACC 233 Jensen's
Inventory Shop, and HIS 110 Wright Brothers. The rest of the registered library
is retained for operators. An opted-in account's feed and playback renewal use
the same shortlist for study slots. The feed mixes ready Reels from the account's
entertainment catalog with the reviewed lessons, targeting two study slots out
of every three when both types are available. Missing lessons are omitted.
The demo never falls back to private lessons or on-demand generation. Earlier demo sessions retire
cards and gates from the former lineup without recording quiz grades.

The feed issues up to one occurrence per reviewed lesson per page, so the
client can buffer the next clip and download the others within its cache budget.
One demo study video with five seconds of server-credited foreground watch
qualifies for a quiz at the next page boundary. The client fetches near that
boundary so prefetch does not put multiple extra pages ahead of a quiz. Questions
rotate through bounded session issuance history. Wrong demo answers update only
the account's generic state and do not queue private regeneration. The personal
feed retains its usual mix and quiz settings.

## Operator registry manifest

`python -m app.core.demo_catalog --manifest MANIFEST.json --apply`
registers already published generic assets. Apply database migration 005 (or the
API's additive `python -m app.core.migrate --apply`) first. It changes no account
flags. It requires 24 distinct ready videos across the four core courses, with six
videos per core course. An optional CS 220 course adds one video. Each video has
two to four quizzes, with quiz IDs unique across the catalog.
Revisions start at 1 and advance by one. Exact replay is idempotent. A rejected
batch leaves the previous registry unchanged.

```json
{
  "schema_version": "1",
  "catalog_id": "shared_demo_v1",
  "revision": 1,
  "courses": [{"course_id": "demo_cs210", "title": "CS210 — Data Structures"}],
  "objectives": [{"objective_id": "demo_cs210_avl", "course_id": "demo_cs210", "title": "AVL balance", "level": "intro", "language": "en", "notation": "general"}],
  "lessons": [{"objective_id": "demo_cs210_avl", "video_id": "published-video-id", "quizzes": ["two full QuizDefinition objects"]}]
}
```

The snippet illustrates shape, not a complete valid batch. The four course IDs
are `demo_cs210`, `demo_acc233`, `demo_his110`, `demo_math235`. Objectives and quiz
IDs begin `demo_`. Each quiz has its lesson's objective ID, scope `shared_generic`,
owner null, and empty source references. QuizDefinition otherwise uses the
[learning contract](learning.md). Each corresponding catalog video must be ready,
shared_generic with no owner, match objective/level/language/notation, have a
30–60 second duration for spoken lessons or 20–60 seconds for the music-led
`math_explainer` format, passed media checks, and an explicit trusted publication
policy. The shorter duration matches the existing math learning contract and
allows the original music-led animation to play in full. Setting private videos
to demo mode never makes them shared.

## Authored generic publication bridge

`python -m app.core.demo_publication --input validated.json --work WORK
--reviews reviews.json --output manifest.json --apply`

This operator-only command consumes completed `pack/<lesson_id>` and
`output/<lesson_id>` artifacts from the authored demo renderer. It never calls a
model, synthesizes narration, renders, or grants approval. It verifies source,
pack, renderer, media, caption, thumbnail and every review-frame hash, then uses
the existing private-bucket byte verifier and atomic Atlas publication fence.
Jobs stay `awaiting_review` on upload failure; they never enter generation queues.

`reviews.json` is an object keyed by lesson ID. Each review must explicitly contain:

- `reviewer: "codex"`, `policy: "agent_reviewed_generic_demo_v1"`.
- `content_digest`: canonical digest of the normalized authored Lesson.
- `checked_facts: true`, `quiz_status: "passed"`, `content: true`,
  `generic_lineage: true`, `visuals: true`, `audio_sync: true`, `assets: true`.
- `renderer_source_digest` matching both render provenance files and current source.
- `video_sha256` and `artifacts: {video, thumbnail, captions, words, quality}`,
  each containing the corresponding file's SHA-256.
- `frames`: map every file in `frame-index.json` to its SHA-256. The beginning,
  action and ending of every scene must be covered.

The thumbnail is `output/frame-01.png`; captions/words are `pack/captions.vtt`
and `pack/captions.json`. Quality is `output/quality.json`. Reviews may be prepared
in stages, but incomplete review objects cannot publish. Catalog metadata records
agent approval and `human_review: "not_performed"`; it never calls agent review
human approval. Generic lineage remains an explicit reviewer judgment.
