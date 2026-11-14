# Agastya status

## Instagram cookie handoff and reopening — November 14

- Added app-authenticated `/v1/instagram/browser-session` using the existing
  single-attempt browser-cookie verifier, owner-bound encryption, attempt fencing
  and cooldown. Failed replacements preserve a previously working connection.
  The Expo preview proxy allows only the new POST route; UI wiring is delegated
  to the mobile workstream.
- Added synthetic SDK/database restart and playback freshness regressions.
  Focused browser-session/restoration/social/playback tests: 28 passed against a
  private disposable Mongo replica set on localhost:27029, with provider calls
  mocked. The real pinned SDK restoration test prohibits network connections.
  Initial SQLite checks: 13 passed. Proxy test: 1 passed with Node 24. Ruff passed.
- An initial test attempt against the previously used localhost:27027 failed
  because that server was no longer the disposable rs0 instance; it was untouched.
  Created a separate 512MB test container for the successful tests and removed
  only that container afterward.
- Documented media expiry versus authentication and the official professional-
  account API boundary in decision 011. No real cookie login, provider call,
  new OAuth implementation or phone-session longevity claim is part of these tests.

## Selected video worker batches — November 14

- Added optional `job_ids` to Atlas/local video claiming and `run_once`; empty
  selections claim nothing, and expiration/retry processing cannot mutate other jobs.
- Demo workers accept repeated `--video-job-id` through `scripts/run-demo.py`.
  Private `VIDEO_GENERATION_JOB_IDS` persists a comma-separated selection across
  restarts; explicitly empty denies all, absent preserves the full queue.
- Ran `.venv/bin/python -m pytest app/modules/videos/tests/test_job_allowlist.py
  app/modules/videos/tests/test_retry.py app/modules/videos/tests/test_video_pipeline.py -q`
  from `services/api`: 29 passed. Ruff checks and `git diff --check` passed.
- Atlas query-scope tests used mocks. The separate `test_atlas_repository.py`
  integration suite skipped all five tests because no disposable Mongo URI was
  configured. No cloud/provider calls or video rendering were run for this change.

API/recommendation implementation and its verification are tracked separately in
[AGASTYA_API.md](AGASTYA_API.md) to avoid overwriting the concurrent video workstream.

Status: video runtime implemented; both local fixture and live Claude/ElevenLabs
renders passed. Hosted publication and iPhone acceptance remain unverified.
Earlier planning notes below are historical.

## Completed

- Added [video-generation TRD](../TRD_VIDEO_GENERATION.md) covering generation
  contracts, both boilerplates, Claude's API-authenticated agent pipeline,
  ElevenLabs narration/captions, isolated rendering, durable jobs, publication,
  acceptance checks, and optional separate-chat ownership.
- Added [proposed decision 001](../decisions/001-video-generation-pipeline.md).
- Captured the requested Minecraft background, bottom Peter/Stewie characters,
  middle captions, and Peter-question/Stewie-correction teaching dynamic.
- No runtime implementation or live generation work recorded yet.

## Commands and verification

- Ran `git status --short` before editing; working tree was clean.
- Inventoried repository Markdown with `rg --files`; read root/renderer/video
  instructions, project/task guides, contracts, integration guidance and references.
- Reviewed official Claude Agent SDK, ElevenLabs timed-speech, and Remotion
  media/still-render documentation. This verifies documentation only.
- Ran `git diff --check`; passed for tracked changes. A `python3` documentation
  check parsed both JSON examples, resolved all 13 relative links across the three
  changed documents, and checked code-fence balance; all passed.
- No runtime tests, provider calls, renders, or iPhone playback tests were run.

## Interfaces and fixtures delivered

- TRD includes proposed internal GenerationBrief, storyboard, timed lesson,
  scene-package, audio/caption, background-selection, and quality-report shapes.
- Includes illustrative synthetic JSON snippets, not executable schema/fixture
  files. Existing public contracts are unchanged.
- Runtime schemas, provider adapters, templates, and fixtures remain pending.

## Dependencies and blockers

- Actual Peter/Stewie voice IDs, character art, and varied approved Minecraft
  recordings are not selected or validated; placeholders may unblock development.
- Claude/ElevenLabs credentials and model/version choices need live preflight.
- Request canonical-objective lookup from Amogh if existing service output does
  not supply level/language/notation. Do not guess academic metadata.
- Coordinate root JS workspace/dependencies and player safe areas with Adi.
- Verify container/VM execution and generated-code isolation before rendering
  model-produced code. Actual iPhone playback remains untested.

## Next actions

- Start with TRD phase P0: runtime schemas and one synthetic lesson/storyboard
  shared by the two formats; then manually authored boilerplates and narration.
- Follow [your task guide](../tasks/AGASTYA.md) for integration and jobs milestones.

## Video implementation update — November 14

- Added validated brief/storyboard/source schemas, both linked-list fixtures,
  Claude structured generation/review/repair, ElevenLabs timestamped speech,
  scope-aware audio caching, exact phrase cues, word captions and amplitude data.
- Added trusted pointer-state snapshots after live testing exposed incorrect
  model-reconstructed state. Generated scenes draw these snapshots inside Docker.
- Built the standalone Remotion package, two templates, asset staging, Docker
  broker, final MP4 checks, frame previews and digest-bound publication review.
- Added Atlas jobs/catalog/outbox adapter, explicit local SQLite fake, lease
  fencing, bounded retries, cancellation, transactional ready publication,
  private Supabase storage adapter, video router and feed reader adapter.
- Root `.env` is loaded first, `services/api/.env` supplies fallback voice settings.
  API keys are not logged. User approved Roger/Daniel/Alice stock substitutes;
  their IDs were verified in Chrome and subsequently by the ElevenLabs API.
- Copied user parkour and downloaded requested Wikipedia character artwork into
  ignored `.local/video-assets`; original Downloads files are preserved.
- Fixture exports: visual 44.245 seconds, dialogue 44.651 seconds, both full
  portrait H.264/yuv420p and AAC48k. These are macOS narration with estimated
  captions, not live-provider acceptance. Current art uses speech bounce/glow,
  not an animated mouth rig. The later live dialogue adds calibrated amplitude-driven
  mouth overlays.

### Verification and handoff

- Video pytest with disposable local MongoDB replica set: 28 passed. Local
  fixture repository is explicitly a fake. Hosted Atlas is not yet verified.
- Ruff passed; renderer test/audit evidence and media paths are maintained in
  [VIDEO_VERIFICATION.md](../VIDEO_VERIFICATION.md).
- Exported `VideoService`, `run_once`, `generation_recipe`, `create_router`,
  `FeedVideoReader`, `AtlasVideoRepository`, `SupabaseVideoStorage`, and the CLI.
- See [video runtime README](../../services/api/app/modules/videos/README.md) for
  exact commands, mounting interfaces and review/publication workflow.
- Shared main.py/core/worker code was preserved. Core now exposes an ordered
  `--include-videos` index setup hook; repeat application passed against local MongoDB.
- Live results: explainer 48.704 seconds; dialogue 54.571 seconds. Both passed
  codec, frame-rate, duration, loudness/peak and representative-frame checks.
  ElevenLabs raw alignment supplied captions. Stock substitutes are disclosed.
- Claude-generated graph geometry failed review; the final root owns tested
  pointer geometry/code and clips generated phase animation to a protected band.
  See decision 003 for this deliberate limitation of the broader TRD scene proposal.
- Remaining: register the
  academic resolver/router/feed reader and video-outbox consumer; verify hosted
  storage and phone playback when those integrations are available. No public
  upload, real authentication or iPhone playback has been claimed.


## Research-driven generation update — November 14

- Reviewed the supplied engagement brief against primary research: Guo's MOOC
  engagement paper, Szpunar's lecture-testing experiments, Donoghue/Hattie's
  learning-technique meta-analysis, D2Q, and the accessible Kang and seductive-detail
  abstracts. Full-text access limitations and transfer-to-feed caveats are in
  [VIDEO_ENGAGEMENT_RESEARCH.md](../VIDEO_ENGAGEMENT_RESEARCH.md).
- Added versioned hook/prediction/reveal/retrieval/feedback structure, brief screen
  text, measured opening limits, grounded reveal/feedback checks and model content
  review. New generation requires the structure; old artifacts remain readable.
- Added actual two-second prediction and three-second recall pauses. Captions,
  trace cues and character timing share the shifted audio clock. Inspection found
  captions crossing same-speaker segment boundaries; fixed and regression-tested
  this so preceding answer text cannot carry into a recall question.
- Renderer hides answer-bearing code/trace/custom scenes during questions, preserves
  captions, and defaults new dialogue to a concept-only background. Explicit
  VIDEO_BACKGROUND_MODE=gameplay retains the original background experiment.
- Added policy/system/timing identity to generation recipes, exported Storyboard's
  additive schema, updated both synthetic fixtures, documented decision 004 and
  retained public feed/quiz/academic interfaces. No new service or dependency.

### Commands and results

- `services/api/.venv/bin/python -m pytest -q` (from services/api): 34 passed,
  4 skipped because API_TEST_MONGODB_URI was not configured.
- `.venv/bin/python -m pytest app/modules/videos/tests -q`: 36 passed, 4 skipped
  because VIDEO_TEST_MONGODB_URI was not configured.
- `.venv/bin/ruff check app/modules/videos`: passed.
- `npm test --prefix services/renderer`: 14 passed.
- `git diff --check`, runtime-versus-exported Storyboard schema comparison, and
  changed-document relative-link checks passed.
- Built `hackumass-renderer:engagement-v1` with Docker. Both fixture previews
  rendered; these use macOS speech and estimated alignment. Those previews were
  inspection inputs, superseded by the caption-boundary and character-spacing fixes.
- Live `generate --prepare-only` tested Claude and ElevenLabs with only the
  synthetic linked-list brief. The initial structured-output run exhausted three
  repairs (wrapper object, opening word counts). Improved prompt/combined error
  feedback; subsequent scripts passed model content review. Dialogue used one
  measured-duration repair. No unlimited retry was added.
- Final live commands use `VIDEO_RENDER_IMAGE=hackumass-renderer:engagement-v1`
  with `generate --format visual_explainer` and `--format dialogue_gameplay`,
  output `.local/video-runs/engagement-live-v1`. Stock voices remain disclosed.
- Both prepared live audio tracks were checked for actual zero-valued PCM during
  the interiors of the 2/3-second pauses, and caption groups were verified not to
  cross narration-segment boundaries.

### Interfaces, safeguards and limits

- Exported internal TeachingBeat/Storyboard.teaching_beats, timed teaching beats,
  pause_after, timed_teaching_beats, timing_issues and the teaching_checks manifest.
  These are structural/production checks, never measured engagement scores.
- Applied CodeGuard: no credentials added; synthetic material only in provider
  tests; model strings stay untrusted and bounded, rendered as React text. Generated
  code retains the no-network, credential-free Docker boundary and human publication
  gate. Existing unrelated domain implementations were preserved.
- No grade, mastery, feed event, ranking, bandit or spaced-review behavior changed.
  Spoken self-checks are ungraded and do not manufacture quiz attempts.
- No engagement or learning uplift has been measured. iPhone playback, hosted
  publication, human listening review and general-subject animation remain unverified.
  The live narration still has a procedural/code-heavy style; reference videos will
  help define the next voice/copy/animation quality pass.

### Final local render evidence

- Live visual explainer: 57.984 seconds; live dialogue: 55.211 seconds. Both
  passed H.264/yuv420p, 1080×1920, 30 fps, AAC48k and loudness/peak checks.
- Inspected opening and recall/pause frames from both final renders. Caption
  boundaries now isolate recall from the preceding explanation. Dialogue character
  labels no longer overlap the stock-voice disclosure.
- Final files: `.local/video-runs/engagement-live-v1/visual_explainer/output/lesson.mp4`
  and `.local/video-runs/engagement-live-v1/dialogue_gameplay/output/lesson.mp4`.
  The folders also contain private storyboards, reviews, timed packs, frames and
  quality reports. All generated media remain ignored by Git.
- Updated the existing local `hackumass-renderer:0.1` tag to the tested
  `hackumass-renderer:engagement-v1` image. No hosted deployment or publication.
- Both outputs remain `validating`, with human review pending and iPhone playback
  unverified. These establish local pipeline/media operation, not learned engagement
  gains or production integration. The visual draft's screen questions are terse;
  editorial polish remains part of reference-video calibration.

## 2026-11-14 — User reference videos, imagery and third space template

### Implemented scope

- Inspected all three supplied examples through 12-frame contact sheets and local
  Whisper base.en transcripts. The comparison covers composition, visual changes,
  captions, conversational cadence and continuous spatial motion; raw media and
  transcripts stay under ignored `.local/reference-analysis` or original Downloads.
- Added `reference_v2` continuous-shot presentation while preserving explicit
  `guided_v1`. The new dialogue has full-frame muted parkour, top word highlights,
  one active cutout, larger trusted diagrams and varied concrete narration. Removed
  persistent title/name/progress UI from this presentation. Generated a separate
  standing Stewie cutout with the imagegen skill, saved as
  `.local/video-assets/stewie-standing-v2.png`; the original bike asset is preserved.
- Rebuilt the image-led format around photographs, camera movement, image-aware
  focal points, establishing views and close-ups. Added `space_explainer` with
  deterministic depth-projected stars, spiral particles, luminous filament networks,
  nebula layers, solar-system geometry, camera push/pull/orbit/drift and NASA textures.
  These are authored illustrative scenes, not a scientific simulation or measured map.
- Claude now proposes public image queries, selects candidate IDs from NASA/Openverse,
  views downloaded images, and plans per-shot framing. Server-side retrieval checks
  exact CDN host, HTTPS, no redirects, byte/pixel bounds and raster signatures before
  JPEG normalization. Alternate candidates are retried after download or visual
  rejection. The renderer still has no network, provider token or application secret.
- Actual live checks caught and rejected an irrelevant NASA equipment image and a
  museum model substituted for a living animal. Search relevance, alternate selection
  and visual inspection were added from those failures. Model reviews are fallible:
  final examples also received recorded editorial corrections to unsupported closing
  phrases. Content review is now bound to the exact storyboard digest.
- General subjects use `trace_kind=none`; linked-list trace events remain validated
  and visible during every event-bearing segment. Cues must be strictly chronological
  before narration is purchased. No quiz scores, mastery or feed ranking changed.

### Interfaces and handoff

- Exported internal `ImageRequest`, `Shot`, `ImageSelection`, `ImageReview`,
  `ImageFraming`, `Brief.presentation`, `Brief.trace_kind`, and the revised schemas.
  New runtime format enum: `space_explainer` in videos and feed candidates.
  Decision 005 and learning/shared contract notes explain the integration impact.
- Adi: ordinary MP4/VTT playback interface; no mobile navigation change. Amogh:
  `space_explainer` may be suggested for relevant approved briefs; general subjects
  require `trace_kind=none`. No edits to their domain code/contracts or root JS config.
- `VIDEO_BACKGROUND_MODE=auto` selects gameplay for reference dialogue; explicit
  overrides still work. `--storyboard-feedback PATH` versions editorial direction.
  Reference scenes use the authored shot renderer; generated custom JSX remains
  limited to the earlier guided presentation.
- Added generic reference storyboards and briefs for linked-list reversal,
  leatherbacks (NOAA source), and cosmic structure (NASA source). The local fake image
  adapter emits synthetic color fields and makes no network requests. Fixture packs
  retain the nonpublishable fixture flag.

### Commands and checks actually run

- `docker build -t hackumass-renderer:reference-v4 services/renderer` and v5 after
  image-aware framing refinements: succeeded, no service/dependency additions.
- Live CLI `generate --prepare-only` for all three new briefs: exercised real Claude,
  ElevenLabs, image search/download/selection and image inspection. Provider failures
  and schema/framing repair diagnostics remain in the private run directories.
- `generate --fixture --prepare-only --brief fixtures/learning/reference-cosmic-web-brief.json
  --format space_explainer`: passed with synthetic local image/audio adapters.
- `cd services/api && .venv/bin/python -m pytest -q`: 34 passed, 4 skipped;
  disposable MongoDB was not configured for this run.
- Video module test suite and renderer validation test suite expanded for reference
  semantics, hidden/reordered traces, image SSRF/redirects/oversized payloads,
  visual-rejection retry, cache verification, real multimodal shot payloads, and
  malformed scene/framing data. Final totals are recorded below after the last run.
- `scripts/export-api-contracts.py --check`: verified 13 API-owned artifacts.
  Brief/Storyboard schema equality is also covered by the video tests.
- Several preview runs were intentionally superseded after visual inspection:
  museum-model imagery, cropped-out animal head and an irrelevant space texture
  were not accepted as final quality. Two v3 previews passed media checks; the
  superseded space preview and initial full image render were stopped for corrected runs.

### Limits

No hosted publication, deployment, real iPhone playback, new Atlas acceptance run,
measured retention/learning experiment, or authentic character voice is claimed.
The voices remain configured stock substitutes. Cutouts are animated by simple
entrances and audio amplitude, not phoneme lip sync. Automated source/crop review
can still miss problems, so human publication review remains mandatory. The space
style is closer in depth/motion, but does not claim professional VFX parity.

### Final verified local deliverables

- `.local/video-runs/reference-v4/dialogue_gameplay/output/lesson.mp4`: **34.752s**.
- `.local/video-runs/reference-v4/visual_explainer/output/lesson.mp4`: **37.141s**.
- `.local/video-runs/reference-v4/space_explainer/output/lesson.mp4`: **39.145s**.
- All three passed 1080×1920, H.264/yuv420p, 30 fps, AAC48k, duration, integrated
  loudness and true-peak checks. Final packs, bounded captions, chronological events
  and all artifact digests verified. Sampled final contact sheets were inspected
  across each complete clip. Whisper checked the speech automatically; no human
  listening review or iPhone test is claimed.
- The space sample received one explicit post-render editorial cut: 89 frames
  removed the second copy of an adjacent repeated sentence. Video, narration,
  captions, shot/segment timing and hashes were updated together and revalidated.
  The original render, measured cut and source image ID are retained privately in
  `space-before-editorial-trim.mp4` and `editorial-trim.json`. A new source validator
  rejects immediately repeated long narration sentences before future TTS calls.
- The image-led sample uses live-selected USFWS leatherback and credited jellyfish
  photographs, with actual image-aware framing. Corrected the distinction between
  normalized focal points and CSS object-position so a requested head crop stays
  in frame. Each run includes `image-credits.json`, source selection/review records,
  and a `post_render_audit` in its generation manifest.
- Final video suite: **61 passed, 4 skipped** (no disposable Mongo replica set).
  Shared API suite: **34 passed, 4 skipped** (no disposable MongoDB).
  Renderer suite: **22 passed**. Ruff and `git diff --check` passed; exported runtime
  schema check verified 13 artifacts. No extra provider or database service was added.
- Default CLI brief now selects reference presentation; an additional narrator
  linked-list fixture keeps default offline `--fixture` operation coherent.
- Authored space rasterization required more local compute. Its resource profile is
  now four bounded CPU cores with a 1600-second render cap and 30-minute pipeline
  deadline; other formats retain two cores, 1100-second render cap and 20-minute
  pipeline deadline. Network, filesystem, memory and process restrictions remain.
- Local `hackumass-renderer:0.1` now points to tested `reference-final` image
  `sha256:2ef97934461ac043bbae3d8cc6fed749cc397e0d5b913e066f979b10652cbf15`.
  Existing generated outputs retain their actual source renderer IDs. No cloud
  deployment or media publication was performed. All outputs remain review-pending.


## November 14 — reference quality revisions and minimal math

Implemented locally, in the existing Remotion + Python harness. No deployment or
publication. Kept unrelated working-tree changes intact.

- Video planning, selection and visual review use `VIDEO_CLAUDE_MODEL`, default
  `claude-opus-5-5`. Actual live response model IDs confirmed Opus 5.5. Switched its
  tool choice to auto after verifying the provider rejects forced tools.
- Added `reference_v3`: dark dialogue overlays, four speaker changes/two snarky
  Stewie turns, user-requested 1.08× tempo with remapped captions and trace cues;
  explicit bounded opening-mistake diagrams and visible None/head pointer states.
- Photo selection now inspects actual candidate images, requires four distinct
  scene assets, rejects URL/content/perceptual duplicates, requests documented
  1024px Flickr sizes, rejects undersized images, and reviews final framing.
- Space now has different authored geometries for galaxies, hierarchy, gravitational
  gathering, sheets, wide void maps and a filament close-up. Final scene differs
  from the opening. Sampled-frame review caught layout/caption defects and drove
  concrete repairs. Rejected drafts remain local diagnostics, not approved outputs.
- New `math_explainer`: trusted matrix dot products (2–3 rows/columns), independent
  renderer arithmetic verification, smooth factor/product/result motion, and
  licensed music retrieval from a curated allowlisted catalog. No source soundtrack
  reuse. The first 34-second render was rejected by the user for visual clutter.
  Their correction now drives a minimal 21-second version: much larger numbers,
  one title, no explanatory prose/footer. Attribution moves to CREDITS.txt.
- Updated learning contracts/schemas and backend format enum. No separate mobile
  category/navigation integration is claimed; Adi can label `math_explainer` as
  “Math / text animation” if a format picker is added. Public playback remains MP4.

Validation actually run:

- `PYTHONPATH=services/api services/api/.venv/bin/python -m pytest services/api/app/modules/videos/tests services/api/tests -q`
  → **106 passed, 8 skipped** (live Mongo unavailable), one existing dependency warning.
- `npm --prefix services/renderer test` → **28 passed**, including independent
  arithmetic rejection and the math-only 20-second minimum.
- `services/api/.venv/bin/python scripts/export-api-contracts.py --check`
  → **13 artifacts verified**. Runtime Brief/Storyboard JSON schemas re-exported.
- Revised synthetic storyboard fixtures all validated against their matching briefs.
  `generate --fixture --prepare-only` for math completed with a synthetic tone and
  no model/music calls; fixture mode remains explicitly marked.
- Live CLI generation exercised Opus, ElevenLabs, Openverse/NASA, candidate-image
  selection, licensed music retrieval, network-free Docker rendering and ffprobe/
  loudness validation. Network/API and draft-quality failures were handled locally.
- Docker builds `hackumass-renderer:reference-v5` and `reference-v6` succeeded.

Completed v5 local clips under `.local/video-runs/reference-v5/<format>/output/lesson.mp4`:

| Format | Duration | Result |
| --- | ---: | --- |
| dialogue_gameplay | 41.835 s | 1080×1920, 30 fps, H.264/yuv420p, AAC 48 kHz; media and sampled Opus review passed |
| visual_explainer (finance) | 38.869 s | Same profile; four different photos; media and sampled Opus review passed |
| space_explainer | 46.080 s | Same profile; six spatial modes/two NASA images; media and sampled Opus review passed |

Actual final MP4 frames were also extracted and inspected locally. Finance is a
hypothetical $1,000 / 10% annual-compounding example, $1,210 vs $1,200 simple interest,
with no return prediction. Math provenance, source limits and research qualifications
are in decision 006 and VIDEO_ENGAGEMENT_RESEARCH.md.

Human aesthetic feedback remains pending. Sampled frames do not establish smooth
motion or voice quality; no engagement/learning lift is measured. iPhone playback,
cloud storage, and mobile-category integration remain unverified. Stock character
voices/cutouts remain approximations, not accurate character voice cloning/lip-sync.

Minimal-math follow-up: the user explicitly overrode the previous prose-heavy review
rubric. `minimal_math` now requires a visual question (unfilled product) and visual
payoff (completed product), not a written hook/rule. The Opus frame review passed
with no blocking issues; it confirmed sampled arithmetic and highlight correspondence.
The new plan selected Cylinder Six. One network-interrupted review was retried;
no rejection was relabelled as approval. Minor bracket-padding polish remains a
nonblocking note. The 21-second full-resolution render is under reference-v6.

Final minimal-math output completed:
`.local/video-runs/reference-v6/math_explainer/output/lesson.mp4` — **21.013 s**,
1080×1920, 30 fps, H.264/yuv420p, AAC 48 kHz, −15.7 LUFS / −2.56 dBFS true peak.
Media checks and the corrected Opus sampled-frame review passed; actual MP4 frames
were extracted and inspected. Attribution is beside the MP4 in `output/CREDITS.txt`.
Human aesthetic review remains pending. Local renderer default `hackumass-renderer:0.1`
now points to the verified v6 image
`sha256:1946c44befa73b279ab423b9587ebd8fd2dd6e06368c3aa645250807357379ac`.
Final Ruff and `git diff --check` passed. No credentials or generated MP4s added to Git.

## November 14 — branch push verification

Prepared all current source, contract, fixture and documentation changes for
`feature/agastya-learning-engine` at the user's request.

Commands rerun before committing:

- `PYTHONPATH=services/api services/api/.venv/bin/python -m pytest services/api/app/modules/videos/tests services/api/tests -q`
  → 106 passed, 8 skipped because a disposable MongoDB test database is not configured;
  one Starlette/httpx deprecation warning.
- `npm --prefix services/renderer test` → 28 passed.
- `services/api/.venv/bin/python scripts/export-api-contracts.py --check`
  → 13 schema artifacts verified.
- `git diff --check` → passed.
- Checked all 63 changed/new files for common credential patterns and prohibited
  media/key extensions → no matches. Ignored local outputs remain outside Git.

This verification did not rerun live providers, cloud deployment, or iPhone playback.
The interfaces, fixtures, and outstanding integration work remain documented above.

### Incoming main planning notes

- Follow [your task guide](../tasks/AGASTYA.md).

## Recommendation proposal update — November 14, 2026

- Added a post-demo plan for contextual template selection, bounded adaptive
  study insertion and calibrated recall scheduling to PROJECT.md, with primary
  research references and explicit limits on transferring findings to this app.
- Added unchecked G7 tasks covering instrumentation, synthetic evaluation,
  delayed learning outcomes, separate template/timing pilots and rollback.
- This is documentation only: no new runtime interfaces, schema fields, fixtures,
  trained model, provider integration or learning-improvement result is delivered.
- Dependencies: Adi for proposed feedback/preferences UI; Amogh for any additional
  objective metadata; repeated real retrieval/exposure data for pilot validation.
  Contract and migration proposals remain to do before implementation.
- Used an isolated checkout of main to preserve concurrent video work in the
  existing feature checkout. Read project/task/contracts/integration guidance.
  `git diff --check` passed. A `python3` documentation check verified all four
  changed documents, 17 local links/anchors, balanced code fences and 13 unchecked
  personalization tasks. No runtime tests or provider/device checks were run for
  this documentation-only change; INTEGRATION.md acceptance remains required.

## Atlas branch integration — November 14, 2026

Fetched every remote branch and merged all distinct heads into the learning-engine
history: main `8beaca9`, Adi Atlas `7b2d229` (includes his mobile/private-feed and
Instagram branches), and Amogh `ebe424a`. `git branch -r --no-merged HEAD` is empty.
Merged in an isolated worktree before updating the active branch; preserved both
sides of the main/status conflict and the user's uncommitted video work.

### Implemented

- `app.runtime:create_app`: one Mongo client, Supabase identity bridge, profile and
  entertainment routers, entertainment projection into the unified feed, shared
  authentication/rate limiting, and safe owner-error responses.
- Core current-user dependency supports Adi's asynchronous verifier and existing
  synchronous fakes without running synchronous database calls on the event loop.
- Ordered `003_identity_entertainment` delegates to Adi's installer. Startup checks
  existing schema/index readiness read-only, including Adi's preinstalled schemas.
- `jsonschema==4.26.0` is now a runtime dependency; regenerated lock offline and
  retained `pymongo==4.15.5`. Production requires stable catalog cursor signing.
- Cross-stream integration repair: Amogh's PowerPoint slide-label f-string used a
  backslash expression unsupported on the shared Python 3.11 runtime. Replaced
  only that expression with equivalent concatenation; no ingestion behavior change.
  This compatibility edit is recorded here for Amogh's handoff.

### Commands actually run and results

From `services/api`, using the existing API Python environment:

- `python -m pytest tests app/modules/auth/tests -q` with both
  `API_TEST_MONGODB_URI` and `MONGODB_TEST_URI` pointing at the disposable loopback
  replica set: **55 passed**. Includes integrated HTTP auth/catalog/feed,
  cross-user access, restart persistence, duplicate/conflicting migrations and
  real transaction/validator checks. Supabase HTTP is mocked, not live login.
- `python -m pytest app/modules/curriculum/tests app/modules/canvas/tests -q`:
  **81 passed** after the syntax compatibility fix.
- `python -m pytest app/modules/curriculum/tests/api_handoff.py app/modules/entertainment/experiments/test_preview_api.py -q`:
  **10 passed**, synthetic external-provider responses.
- `python -m pytest app/modules/videos/tests -q`: **72 passed, 4 skipped** without
  the Mongo test variable. Reran `test_atlas_repository.py` with
  `VIDEO_TEST_MONGODB_URI` against the disposable replica set: **4 passed**.
- Optional Instagram probe suite: **4 passed, 1 failed** because `instagrapi` is
  absent from the shared environment. It is an optional provider experiment,
  not an integrated-runtime dependency; no Instagram retrieval was attempted.
- Ruff on changed core/runtime/tests, `uv lock --check --offline`, and
  `git diff --check`: passed. Local MongoDB was 8.0.38 on port 27029, with random
  test databases cleaned by the suites; no application/Atlas data was modified.

### Configuration and remaining work

Adi's hosted initialization evidence is in `docs/ADI_ATLAS_SETUP.md`. In this
checkout, `services/api/.env` has an empty `MONGODB_URI`; hosted preflight stopped
before connecting. Requested the working local env-file path (no secrets in chat).
No hosted runtime, real Supabase login, deployment, or iPhone acceptance is claimed.

Run instructions are in `services/api/README.md`. Configure the Atlas URI and
Supabase publishable auth configuration to start `app.runtime:create_app`.
Academics remains Amogh's local snapshot persistence; his Atlas schemas/repository
are still needed. Video Storage signing, academic router composition, generation
handoff and quiz content provisioning remain separate integration work. This
change does not invent academic database schemas or publish media.

## November 14 — semantic motion, minimal math and cost-aware review

Implemented the user's next visual direction in the harness, prompts, schemas,
authored Remotion scenes, synthetic fixtures and review gates. New demo subjects:
psychology (sunk-cost movie ticket), personal finance (pay-in-four obligations),
biology (enzyme mechanisms) and geometry (Pythagorean rearrangement). Historical
matrix/linked-list/astronomy paths remain supported. Mobile IDs/wire playback are
unchanged; `space_explainer` also carries the authored biology scenes.

- Transparent dialogue diagrams, no dialogue music, original concept-related snark.
- Trusted installment arithmetic and useful changing diagrams replace stock photos.
- Minimal geometry, exact endpoint-area tests, licensed instrumental music with
  attribution beside the MP4. No credit footer or prose rule cards.
- Biology uses distinct binding/reaction/reuse/competition/concentration/heat
  mechanisms, short yellow bouncing captions and minimal labels. Preview defects
  drove reusable path/label repairs; failed reviews were never relabeled passes.
- Fixed editorial tempo remaps all speech timestamps; semantic scenes longer than
  eight measured seconds trigger bounded shortening, not more audio acceleration.
- Opus5.5 remains the video-specific model. Exact-input model cache covers model,
  prompt, schema, payload and attached pixels; cache hits revalidate without HTTP.
  Audio caches retain per-segment WAV/alignment. Fact reviews bind to the actual
  brief as well as the script; a stale-review regression was found and fixed.
- Explicit `--storyboard-file` supports targeted edits while retaining the live
  content/render gates. Renderer defects stop for code repair, rather than wasting
  calls rewording a script. Live CLI rendering requires a current passing review.

Research and integration details: decisions/007-semantic-motion-video-templates.md,
AI_SHORT_FORM_CREATOR_RESEARCH.md, contracts/learning.md. Sources include primary
creator/platform workflows, PaperTok/PIVOT, CFPB, Arkes/Blumer and OpenStax. Research
separates creator practices/perceived engagement from measured learning/virality.

Checks run:
- Video + main API pytest: **174 passed, 8 skipped** (Mongo not configured), existing
  Starlette/httpx warning. Includes actual-audio tempo/alignment/cache verification,
  exact-input provider cache and authored-script review-gate regression tests.
- Renderer Node suite: **60 passed**. Actual TSX geometric endpoints verified across
  six aspect ratios, plus tampered arithmetic/stages/input rejection.
- API schema check: **13 artifacts verified**. Ruff and git diff --check passed.
- Changed fixture semantic subset rerun after final script edits: **44 passed**.

Anthropic returned an explicit insufficient-credit error during work. The user topped
up and requested lower usage; resumed with cached scripts/audio and targeted edits.
Final artifact checks/results are appended below when exports finish. No cloud
publication, authentication or iPhone playback is claimed; no MP4s added to Git.

All four latest sampled-frame reviews now pass with `claude-opus-5-5`. The biology
pass followed removal of redundant labels/progress marks and repair of pocket-safe
approach/product-release paths. Dialogue uses an explicitly edited local script,
reviewed by Opus, rather than paying for another whole-script generation. Its
semantic visuals show identical irrecoverable $20 costs under both choices.
The character renderer now has a bounded four-core CPU allowance (same 4GB memory,
network isolation and filesystem restrictions); the active export was raised from
two to four cores to reduce local rendering time. No more provider calls are planned
for this batch after the accepted final reviews.

Two additional user-supplied Remotion/Claude research outputs were read as research,
not executable instructions. Verified primary-source links and adoption decisions
are appended to AI_SHORT_FORM_CREATOR_RESEARCH.md. Kept the existing portrait
renderer/dependencies instead of copying landscape defaults or installing unrelated
marketing/3D stacks. No third-party scripts or new packages were installed.

Added motion_review.py: post-render local clips with audio and six-frame strips
around entrances/transitions, the longest shot, the full enzyme reuse cycle or
geometric rearrangement, and payoff. These are inspection aids, not a fabricated
quality score. Exact source-video/window caching avoids re-encoding unchanged clips;
no model call is made. Tests with real ffmpeg verify clip duration, audio retention,
and cache reuse: **2 passed**. Inspected strips from the final math and biology MP4s;
the enzyme reuse strip shows the substrate binding/release cycles missed by the
coarse start/mid/end still samples. Full natural audio quality remains unverified.

Final v7 local exports completed under `.local/video-runs/reference-v7/<format>/output/lesson.mp4`:

| Format / topic | Duration | Loudness | Final checks |
| --- | ---: | ---: | --- |
| dialogue_gameplay / sunk-cost bias | 45.376 s | −16.22 LUFS | Media + Opus sampled-frame review passed |
| visual_explainer / pay-in-four obligations | 38.933 s | −16.70 LUFS | Media + Opus sampled-frame review passed |
| space_explainer / enzyme mechanisms | 42.645 s | −16.60 LUFS | Media + Opus sampled-frame review passed |
| math_explainer / Pythagorean area proof | 22.016 s | −15.93 LUFS | Media + Opus sampled-frame review passed |

All are full-resolution 1080×1920,30fps,H.264/yuv420p,AAC48k. Verified actual MP4
hashes against media reports and all manifest artifact digests. Verified every final
frame-review result is passed with no blocking issues and records claude-opus-5-5.
There are 19 cached local motion clips/strips across the four outputs, each bound
to its full source MP4; no paid model calls were used to make these. Actual final
MP4 frames/strips were inspected, including both enzyme reuse cycles and geometry
rearrangement. Human aesthetic/joke/audio-naturalness review and iPhone playback
remain unverified; no engagement or learning uplift is claimed.

Final automated suite: **176 Python tests passed, 8 Mongo checks skipped; 60 renderer
tests passed**. 13 API schemas verified; Ruff/diff checks passed. The motion-cache
checks were rerun after their final small validation change (2 passed). Default
local renderer tag `hackumass-renderer:0.1` now points to verified v7 image
`sha256:be6a7d9e0461b264365a95f02b921dce76ec14ae5b6502c37648be051fbfc963`.
Math music: Cylinder Four, Chris Zabriskie, CC BY4.0; attribution/modifications are
in output/CREDITS.txt and must accompany sharing. No generated media or credentials
were committed; these source changes are uncommitted for user review.

### Character voice cloning — November 14, 2026 (verification pending)

User requested actual Peter/Stewie clones and explicitly confirmed rightsholder
permission in chat. Two subagents researched official provider requirements and
prepared/checked source samples. Local samples and provenance are Git-ignored in
`.local/voice-cloning/`; no downloaded media or credentials were committed.

- Stewie source: official Family Guy YouTube clip `IPBvDzLtSDw`, 0–46.95s;
  removed the sung outro. Peter source: `GospVDNp6EM`, 0–49.65s;
  removed the later stormtrooper dialogue and shout. Both PCM16 mono 44.1kHz.
  Speaker selection used video frames and local Whisper word timestamps, not a
  claimed listening review. Exact hashes/ranges: `sample-provenance.json`.
- Created both account-specific ElevenLabs IVC records through `/v1/voices/add`.
  Stewie ID `kT3KTNZMcQV83f2BidLc`: `requires_verification=false`; live timestamped
  synthesis succeeded. Peter ID `ofC1e6Dig266fjZT6JwH`:
  `requires_verification=true`, `is_verified=false`. Its UI requires a fresh
  voice-owner recording. User said they will arrange verification. No Peter
  synthesis, fake verification, or replacement clone was attempted.
- Generated Stewie preview and all five Stewie lines for the frozen v7 sunk-cost
  storyboard using the existing narration/cache adapter and `eleven_multilingual_v2`.
  Preview: 6.177s, 23/23 words recognized by local Whisper, non-silent.
  Lesson lines: 19.381s total; IDs, hashes, text, durations and caption alignment
  passed checks. Likeness/naturalness still require listening review.
- API subscription lookup returned `missing_permissions` for `user_read`;
  voice listing, creation, metadata reads and Stewie synthesis succeeded.
  No account permissions were expanded.
- Commands run: private `provider.py clone --role peter/stewie`,
  `provider.py preview --role stewie`, `provider.py prepare --role stewie`,
  local Whisper/FFprobe checks; results are in `stewie-validation-report.json`.
  `services/api/.venv/bin/python .local/voice-cloning/finish_after_verification.py`
  correctly stopped at Peter's verification gate before synthesis/config changes.
  This prepared resumption command checks both provider statuses, reuses the
  frozen storyboard and caches, generates into `.local/video-runs/character-voices-v1`,
  and updates only server voice settings after successful rendering.
- Existing stock-voice configuration and videos remain unchanged. No new complete
  two-character MP4, publication, or iPhone playback is claimed. Remaining work:
  voice-owner verification of Peter, Peter preview, full regeneration, listening
  and final media review. Credentials remain loaded from ignored server env files;
  helper HTTP calls use fixed HTTPS destinations, certificate validation and no
  redirects. Public contracts and application code were not changed for this task.

### Expanded character samples and clone cache revision — November 14, 2026

User requested more samples for both characters and a stronger British Stewie
accent. Added 53.60s from the classic Jolly Farm letter scene
`https://www.youtube.com/watch?v=Uo0lrLtbbyE` (4.45–58.05s; Brian intro/reaction
excluded) to the existing Stewie clone through the official edit endpoint.
Both sample IDs are present; total source speech is 100.55s. Provider still reports
no verification requirement for Stewie. A therapy alternative was retained locally
but not uploaded. Source selection is frame/transcript-based; perceptual accent
improvement remains for user audition, not asserted from transcript checks.

Prepared 54.50s more Peter speech from official `S2dLEU-kjSA` (0–29.90s) and
`zw8zUMjEW0I` (15.00–39.60s), excluding other speakers/outros. Combined local
`peter-expanded-sample.wav` is 104.15s. Extra samples remain local: Peter still
reports `requires_verification=true`, `is_verified=false`; voice-owner verification
is the blocker, not sample duration. No replacement Peter clone was created.
Each role's `*-extra/provenance.json` records exact sources, ranges, hashes and
review limitations. No source audio or credentials are tracked.

Fixed an actual stale-audio issue for edits that retain a provider voice ID:
optional server `ELEVENLABS_<ROLE>_VOICE_REVISION` values now participate in both
the generation recipe and audio-cache identity. Existing unset revisions retain
the previous audio cache identity; fixture narration ignores revisions. Updated
server env example/README, with no public wire-contract changes. The local helper
records Stewie sample-set revision `315b10e5c0820ab5a42a`; the prepared completion
script carries this revision into generation and eventual server configuration.
After Peter clears verification it will add his prepared extra samples, recheck
verification, then rebuild. Current default voice configuration is unchanged.

Fresh `stewie-preview-v2.mp3`: 5.851s, local Whisper 23/23 words, non-silent,
peak −4.9dBFS. All five Stewie lesson lines regenerated (18.352s speech total),
with new revision keys/paths/hashes; no v1 audio reused. Text, voice IDs, hashes,
duration and caption timestamp bounds passed offline checks in
`stewie-validation-report-v2.json`. User was given the new preview to assess accent.

Validation actually run: video-pipeline/narration-tempo/provider-cache/storyboard
override tests **36 passed**. After adding generation-key coverage, focused tempo
test **1 passed**. Ruff check/format and `git diff --check` passed. Private helper
scripts compiled. Previous unrelated working-tree changes preserved. Full updated
two-character rendering, perceptual audio review and iPhone playback remain pending.

User subsequently accepted `stewie-preview-v2.mp3` as “fine for now”; retain clone
`kT3KTNZMcQV83f2BidLc`, revision `315b10e5c0820ab5a42a`, for the final rebuild.
This approval concerns the auditioned voice, not final-video playback or sync.
Peter's subsequent metadata check still reports verification required/unverified.
The request to recreate Peter specifically to avoid verification was not executed;
no duplicate clone, verification recording or substitute voice was created.

### Post-merge preservation check

The active `feature/agastya-learning-engine` branch now includes `46d6aa8` and
all fetched remote tips. SHA-256 checks confirmed all 44 pre-existing changed or
untracked files outside this status file were unchanged; the 186 local status
lines were restored verbatim after the merge. The temporary stash was removed.
On the combined checkout with the user's local video changes,
`cd services/api && .venv/bin/python -m pytest tests app/modules/videos/tests -q`
passed **177 tests, 10 skipped** (Mongo environment variables unset for this final
pass; the separate real replica-set suites passed above). The disposable MongoDB
process was stopped. No remote push, hosted migration, or deployment was performed.

### Hosted connection follow-up — November 14

The user entered the Atlas database credential using the ignored, non-echoing
local helper. `services/api/.env` is ignored and mode 0600; no credential values
were printed or committed. Browser inspection confirmed the expected cluster and
database user. With the user's explicit one-week authorization, added only this
workstation's current /32 IP to the Atlas access list; the entry is Active and
expires `2026-11-21T16:58:18Z`. Existing access rules were preserved.

`PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.auth.atlas_preflight --env-file services/api/.env --report .local/atlas-readiness/hosted-integration-report.json`
ran with network access and reached Atlas, but returned `AUTH_FAILED`. Hostname
and database username match the observed Atlas configuration. Requested correction
of the locally saved database password. No hosted schemas, user roles, passwords,
or application records were changed. The network rule is complete; hosted
runtime verification remains blocked on a valid database credential.

### Hosted Atlas verification completed — November 14, 2026

After the user corrected the locally stored database password, hosted Atlas
verification passed. This supersedes the prior `AUTH_FAILED` blocker.

- Read-only preflight: authenticated connection, replica set, logical sessions,
  identity/entertainment validators and indexes, core migration 001 and video
  migration 002 all passed at `2026-11-14T17:00:54Z`.
- Preflight with `--write-test`: majority transaction commit, snapshot rollback,
  and cleanup of its fresh synthetic probe collection all passed. Report:
  ignored `.local/atlas-readiness/hosted-transaction-report.json`.
- Ran ignored `verify-integrated-runtime.py`: compared all 12 core collection
  validators/indexes with the merged runtime; all match. Applied only the
  additive `apply_identity_catalog` step using Adi's conflict-refusing installer
  and recorded `003_identity_entertainment`. No core/video schemas were rewritten,
  no private application records seeded, and no generation jobs enqueued.
- Integrated factory startup against the actual Atlas database passed. `/health`
  returned 200; unauthenticated identity/catalog/progress requests returned 401.
  The smoke test explicitly injected an unavailable auth verifier: a supplied
  synthetic token returned 503. This verifies database wiring and fail-closed
  boundaries, not live Supabase authentication. Report:
  ignored `.local/atlas-readiness/integrated-runtime-report.json`.
- Credentials remain only in ignored `services/api/.env`, mode 0600. Current
  workstation /32 network access is active through `2026-11-21T16:58:18Z`.

Remaining: local SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are unset, as is the
Storage service credential. Normal `app.runtime:create_app` startup still needs
Supabase auth configuration. No persistent API process or deployment was started.
Academic Atlas persistence and hosted media playback remain unverified as above.

### Supabase publishable configuration verified — November 14

Found the user-provided SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in the root
ignored `.env`; copied only those two values into the backend ignored `.env`,
keeping mode 0600 and preserving all existing provider/Atlas configuration.
This supersedes the missing-auth-configuration blocker above. Service-role/Storage
credentials remain deferred at the user's request.

Ran `PYTHONPATH=services/api services/api/.venv/bin/python .local/atlas-readiness/verify-configured-runtime.py`
with network access: real Supabase Auth settings returned 200 with the configured
publishable key; the normal integrated factory started against Atlas without an
injected verifier. Health returned 200, protected requests without tokens returned
401, and a deliberately invalid token reached live Supabase and returned 401
`AUTH_INVALID`. No account or application records were created. Report is ignored
at `.local/atlas-readiness/configured-runtime-report.json`. A successful real-user
login and hosted Storage remain untested. The smoke-test API stopped afterward.


### User-supplied short-form format audition — November 14, 2026

Created `services/renderer/experiments/format-audition/` as a separate local lab
for the two pasted research briefs. It contains 19 candidate manifests, original
synthetic scripts and authored Remotion/SVG scene mechanisms, plus nine local
candidate SKILL.md files. The skills are saved with this experiment, not globally
installed. All formats remain `awaiting_user_review`; no keepers are inferred.
Existing production formats, public contracts, root lockfiles, app navigation,
server configuration and unrelated working-tree edits were not changed by this task.

The ignored review artifact is `.local/format-audition/index.html`, served locally
at `http://127.0.0.1:8787/` and opened in the in-app browser. It includes 19 players,
script/timing data, storyboard contacts, notes, Keep/Potential/Pass controls,
local browser persistence and JSON feedback export. Choices do not automatically
modify template approval state. Full outputs are under `output/<sample>/lesson.mp4`.
All 19 final MP4s are 720×1280, 30 fps, H.264/yuv420p, AAC/48 kHz, 24.6–33.3 s;
544.2 s total, about 23.7 MB. No media was committed or published.

Live ElevenLabs narration used the configured narrator and existing content-addressed
speech adapter; 76 aligned segments were checked. Scripts/scene code were authored,
not represented as live Opus generation. Five actual `claude-opus-5-5` calls critiqued
rendered contacts and scripts, producing 31 initial findings. Fixed factual/state
contradictions, clipped labels, premature answers, object continuity, catalyst
transformation, list reset/append actions and missing traction mechanism. Retained
intentional result-first openings and the experimental 1.6-second retrieval hold.
`review-disposition.json` distinguishes corrections and editorial decisions.
Revised frames and actual encoded-frame samples were inspected; no final Opus PASS,
full perceptual audio review, or human creative approval is claimed.

Commands actually run from the repository root:
- `PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/format-audition/prepare.py` — live speech, then cached rerun with one corrected circuit line.
- `python3 services/renderer/experiments/format-audition/run.py stills` — final 190 frames rendered in the isolated existing image.
- `PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/format-audition/review.py` — five cached structured critiques.
- `run.py video` — first four exports; intentionally stopped the serial run, then exported remaining disjoint groups with `--only history,inside,map,math,money`, `--only myth,pov,predict,series,skill`, and `--only technology,timeline,variable,versus,what-if`.
- `python3 services/renderer/experiments/format-audition/finalize.py` — normalized full-range renderer output and narration level; initial pixel-format check correctly failed before normalization.
- `python3 services/renderer/experiments/format-audition/verify.py` — **19/19** final media checks passed: codecs/dimensions, duration, full video decode, caption bounds and non-silent non-clipping audio. SHA-256 checks matched every final file to its report.
- `python3 services/renderer/experiments/format-audition/check_motion.py` — actual encoded ball trajectories stay level within 0.13 px; actual pendulum trajectories repeat at 4/8 seconds with <0.05 px mean error. Reports bind to final MP4 hashes.
- `python3 services/renderer/experiments/format-audition/gallery.py` — all 19 cards generated; browser page and layout observed.
- Skill creator `quick_validate.py` — **9/9** skill drafts valid with system Python. Python compilation, `node --check` and `git diff --check` passed. Inline Python verified exact arithmetic and the shown list-copy program.

Applied selected guidance from the inspected TikTok, explainer and typography skill
repositories; exact upstream revisions are in `skill-sources.json`. No third-party
installer or skill script was run. Kept all provider secrets outside renderer
mounts; existing certificate-validating adapters performed synthesis/review. Renderer
ran non-root with no network, read-only inputs/root, dropped capabilities and bounded
CPU/memory/PIDs/file size. No credentials or private course material are in the pack.

Scope limits: these are 2D/2.5D auditions, with explicit proxies for 3D science,
real geography, technology footage, historical reconstruction and generative POV.
Dialogue uses one narrator. Wider suggested Manim/MapLibre/WebGL/B-roll skill packs
were not benchmarked; the nine local skills are drafts, not validated retention
optimizers. Geometry remains authored for each synthetic example; general-topic
parameterization follows selection. Short clips are not production-ready spoken
VideoVariants under the existing 30–60 s contract. User taste/listening review,
iPhone playback, production integration, engagement and learning outcomes remain
unverified. Remaining user decision: which numbered samples to keep, revise or pass.


## Adi branch local iOS build — November 14, 2026

User requested a locally compiled iPhone app from Adi's branch, then deferred
physical-device installation and requested the simulator instead.

- Source: local `origin/adi-private-phone-feed` at `a2c91d4`, exported with
  `git archive` to ignored `.local/iphone-build/adi-a2c91d4`. No checkout switch,
  branch merge, tracked mobile implementation edit, or root lockfile change.
- `npm ci --cache /private/tmp/hackumass-iphone-npm-cache --no-audit --no-fund`:
  installed 518 packages. Used explicit Node 26.12.0; root engine requests Node
  24, so npm emitted an engine warning. `npm run typecheck`: PASS.
- `CI=1 HACKUMASS_INSTAGRAM_PREVIEW=0 HACKUMASS_PREVIEW_API=0 expo prebuild
  --platform ios --no-install`, then `pod install`: PASS, 103 pods installed.
- Xcode 26.3 initially failed compiling ExpoModulesJSI's `withEncodedValue`
  with “sending slot risks causing data races.” Applied a local dependency-only
  synchronous-pointer capture workaround matching Expo issue 52754:
  https://github.com/expo/expo/issues/52754 . Saved exact patch as
  `expo-jsi-xcode26.3.patch` inside the ignored build directory. No global
  concurrency-check suppression, auth change, or credential embedding.
- `xcodebuild -workspace Studyinyourfeed.xcworkspace -scheme Studyinyourfeed
  -configuration Debug -destination 'generic/platform=iOS'
  -derivedDataPath ../../../build-iphone DEVELOPMENT_TEAM=HRSA6MR4U3
  CODE_SIGN_STYLE=Automatic -allowProvisioningUpdates build`: PASS after the
  patch. `codesign --verify --deep --strict` outside sandbox: PASS.
- Physical iPhone was observed paired by USB with Developer Mode enabled.
  User unplugged/deferred installation; no physical app launch/playback claim.
- Simulator xcodebuild with destination iPhone 17
  `29795426-94E8-4815-B684-CD8D55E38AE1`, Debug, derived data
  `../../../build-simulator`, `CODE_SIGNING_ALLOWED=NO`: PASS. Applied local
  ad-hoc signing to the simulator artifact and verified it. Simulator copy
  stalled in CoreSimulatorBridge `clonefileat`; restarting that bridge and
  installing a copy from `/private/tmp/hackumass-studyfeed-simulator` succeeded.
- `xcrun simctl install` and `xcrun simctl launch ... dev.hackumass.studyfeed`:
  PASS. Metro at localhost:8081 returned `packager-status:running`, bundled
  965 modules, and screenshot visually confirmed the native welcome screen.
  Evidence: ignored `simulator-running.png`, build logs, `build-info.json`.
- Running mode: public fixture demo, private Instagram preview disabled; no
  public Supabase auth config was available in this snapshot. Sign-in is
  disabled; scroll to Explore the demo. No live backend/auth/video playback
  acceptance was exercised. Metro remains running for the simulator.
- Device app: `build-iphone/Build/Products/Debug-iphoneos/Studyinyourfeed.app`
  under the build directory. It is a Debug development build requiring Metro;
  phone installation and reachable LAN server setup remain for the user's return.


### Local Reels import prepared — November 14, 2026

- Installed `instagrapi==3.2.12` into the isolated iOS snapshot's
  `.local/instagram-probe/venv`. `pip check` passed; all five existing
  `test_instagram_probe.py` tests passed (synthetic provider responses).
- Opened a user-owned Terminal running the existing bounded, one-page probe,
  followed by `node --import tsx apps/mobile/scripts/prepare-instagram.ts` only
  on successful retrieval. Observed redacted report stage `awaiting_credentials`.
- User must enter username/password/optional 2FA in the hidden Terminal prompts.
  No credentials were read or entered by the agent. No live acquisition yet.
  Existing simulator still uses public fixtures; switching localhost Metro to
  saved Reels remains pending successful import.


### Real Reels simulator preview enabled — November 14, 2026

- User completed private Terminal login. Redacted report confirms authenticated
  retrieval of four Reels, four HTTPS candidates, one page, provider `has_more`
  true. Normalizer produced four items and `next_cursor: null`.
- Replaced the fixture Metro process with `HACKUMASS_INSTAGRAM_PREVIEW=1
  HACKUMASS_PREVIEW_API=0 CI=1 expo start --localhost --port 8081 --clear` in
  the isolated app. Local status endpoint responds; simulator terminate/launch
  succeeded. No LAN/public tunnel or provider credentials in the app.
- This remains a finite saved catalog: further pages and URL renewal are not
  fetched automatically. Native playback of this newly retrieved batch has not
  been observed; user can enter Explore the demo to open the Saved Reels feed.


### iPhone installation completed — November 14, 2026

- User explicitly requested installation after importing real Reels. Connected
  iPhone 15 Pro was available and paired. Built a self-contained Debug app in
  the ignored Adi snapshot, then installed and launched it by USB with
  `xcrun devicectl device install app` / `device process launch`.
- Generated local AppDelegate uses embedded `main.jsbundle` on physical devices;
  simulator retains Metro. Local `.xcode.env.local` enables bundling. The
  snapshot Metro config adds an explicit `HACKUMASS_PRIVATE_DEVICE_BUNDLE=1`
  mode restricted to `export:embed`, iOS, and development bundles. This embeds
  only the already-normalized private catalog for this user's requested phone
  installation; it cannot start a private-catalog network server or release
  export. The ordinary localhost simulator preview remains available.
- First standalone bundle omitted the catalog because this Expo export path
  ignored the supplied `--config` option. Corrected the normal local Metro
  config, rebuilt, and verified all four provider IDs in the final Hermes
  bundle before replacing the phone installation. No tracked mobile files or
  shared lockfiles changed. No provider passwords/session cookies embedded.
- Final native xcodebuild: BUILD SUCCEEDED. Embedded bundle: 5,217,350 bytes,
  four of four imported catalog IDs verified. `codesign --verify --deep
  --strict`: PASS. Device installation and launch: PASS.
- The phone no longer needs Metro or the Mac to open. Internet is still needed
  for Instagram CDN playback. Catalog remains four saved Reels; links can
  expire and no automatic next-page fetch/renewal exists. Sign-in remains
  unconfigured; use Explore the demo. Physical playback is not yet observed.

### Three-voice friction cartoon audition — November 14, 2026

- User requested a more engaging friction counterfactual cartoon, varied voices,
  and college-level topics for future samples. Added isolated experiment under
  `services/renderer/experiments/friction-story`; left production voice settings,
  public contracts, app navigation, existing media and unrelated edits intact.
- Live `claude-opus-5-5` produced story/casting guidance using supplied current
  web evidence. Trend sources do not establish a live TikTok ranking; no such
  claim is made. Editorially tightened to 102 words and added the university
  mechanics relation `mv²/r ≤ μ_s N`, with the fixed-mass/radius condition on
  the 2× speed → 4× force comparison.
- Three actual ElevenLabs stock voices: Laura (narrator), Charlie (shark),
  Callum (coffee driver), using `eleven_multilingual_v2`. No cloned celebrity
  voices. Source storyboard, voice IDs and reproduction scripts are preserved.
- Eleven-shot authored cartoon: sneaker walk/paddle cycle, speech-envelope
  mouths, sliding car with locked wheels, foam contact collision, shoe-force
  close-up, inward turning-force animation, aligned captions and original
  procedural music/foley. This is an illustrative 2D animation, not a numeric
  rigid-body simulation or live physics engine.
- Actual commands: `plan.py` and `prepare.py` with `PYTHONPATH=services/api`
  under the API venv; `sound.py`; `run.py stills`; `run.py video`;
  `finalize.py`; `verify.py`; `check_motion.py`; `preview.py` under system
  Python. An initial JSX typo was corrected before successful renders.
  Initial motion masking included building colors; narrowed the mask to the
  inspected encoded car color, then reran the check successfully.
- Renderer used the existing reference-v7 Docker image, non-root, network off,
  read-only root, four CPUs/4 GiB and existing time/resource limits. The attempted
  six-core update happened after the container had completed and changed nothing.
- Export: `.local/friction-story/output/friction-story/lesson.mp4`, 43.6s
  encoded (43.5s composition), 720×1280, 30fps, H.264/yuv420p + AAC, about
  7.2 MiB. Full decode, caption bounds, duration and level checks PASS; peak
  −1.6 dBFS. SHA-256:
  `eced5bb03dfae2d2eac0caf007b38b9fcbf0b5b864d1769647eb996aed47e98e`.
- Encoded brake-shot check PASS: car translation 35.88px vs expected 35.74px,
  while wheel-relative spoke-image mean delta was 4.96/255. Three distinct voice
  IDs confirmed. This verifies that specific shot, not every physical claim.
- Inspected actual stills and exported frames; fixed a shoe-label overlap.
  Local IAB playback observed advancing to 3.68s, readyState 4, no media error,
  correct dimensions. Physical-iPhone playback and subjective audio/creative
  quality remain unverified; user review is pending.
- Added sample 20 first in `http://127.0.0.1:8787/#friction-story`. Existing
  three browser ratings and notes visibly survived the reload. No sample was
  promoted to an approved template or production catalog.
- Saved current guidance in `services/renderer/experiments/CREATIVE_DIRECTION.md`
  and updated three local candidate skills: varied casting, causal stories,
  and college-level future topics. This is authoring guidance, not an automatic
  production voice-rotation scheduler. `py_compile`, frozen script/cast/reference
  checks and `git diff --check` PASS. Generated media/cache remain ignored.

### Direct friction story, pop captions and reusable story planning — November 14, 2026

- User rejected sample 20's elaborate setup and excess text, then endorsed the
  simpler sample 21 direction as promising. Rebuilt in
  `services/renderer/experiments/friction-story-v2`: cars collide, mom and dog
  slip, a pinched phone falls, and a rope climber makes a "floor record";
  then visual explanations of friction, traction and turning-force demand.
  Some animation quality still needs user review. This is an authored 2D
  cartoon, not a general-purpose physics simulator.
- Frozen narration: 115 words, male ElevenLabs stock voices Liam and Roger,
  `eleven_multilingual_v2`. Captions and essential diagram notation are the
  only on-screen text. Latest render completes the supported landing pose,
  uses collision-induced motion instead of stopping frictionless cars in place,
  and keeps curve-to-tangent motion continuous. Gravity and contact forces
  remain in the counterfactual; same-mass/radius conditions accompany 2v → 4F.
- Added reusable `services/renderer/src/PopCaptions.tsx`, exercised by this
  audition: every new phrase grows quickly, settles, and highlights the current
  spoken word. It is not yet enabled across every production template.
- Commands actually run: `prepare.py` with the API venv/PYTHONPATH;
  `sound.py`, `run.py stills`, `run.py video`, `finalize.py`, `verify.py`,
  `check_motion.py`, `preview.py` under system Python. Rendering used the
  existing isolated reference-v7 Docker image, no network or application
  credentials, non-root/read-only, four CPUs and 4 GiB. Existing webpack cache
  EROFS warning was nonfatal. No dependencies or lockfiles changed for this work.
- Final `.local/friction-story-v2/output/friction-straight/lesson.mp4`:
  44.8s, 720×1280, 30fps, H.264/yuv420p + AAC, peak −1.5 dBFS.
  Full decode, caption timing/bounds, duration and audio checks PASS. SHA-256:
  `65fbc37cd8819ae040173794d30f1880316c8c931d49dfb41b87c29a53e326b5`.
- Encoded motion checks PASS: equal-interval car translation 39.92/39.55px
  with locked-wheel relative pixel delta 6.96/255; equal-interval phone drops
  55.5/101.5px. These check specific shots, not every physical claim.
  Encoded caption outline widths at frames 0/2/8 were 438/629/562px,
  confirming the growth and settle; saved SHA-bound `caption-pop-report.json`.
- Inspected final contact frames and updated sample 21 in the local gallery.
  IAB playback reached 44.8/44.8s, ended=true, readyState=4, no media error.
  Three existing browser ratings survived. Physical-iPhone playback of this
  sample remains untested. Generated media/cache remain ignored and uncommitted.
- New internal authoring interface `generation/story_engine.py` exposes
  `plan_story`, scoped history persistence and `record_feedback`; `story_cli.py`
  runs it locally. Plans contain ordinary goals, causal actions/end states,
  approved fact IDs, 1–2 expectation/reversal jokes and casting direction.
  Three alternatives are checked against recent settings/props, punchlines,
  wording and repeated humor mechanisms, then audited for factual/visual/humor
  issues. User keep/potential/pass feedback stays separate from automated audits.
- The planner is not wired to the public Storyboard contract or production
  feed. New actions still require scene authoring and encoded visual QA.
  History is owner/catalog scoped and single-writer locally; production needs
  a transactional store. Novelty heuristics and model audits do not prove
  originality, funniness, learning gains or engagement.
- Saved the current direction in `experiments/CREATIVE_DIRECTION.md`, updated
  narration/storyboard/format guidance, and added the tenth local candidate
  skill `format-audition/skills/real-world-humor`. Skill validation PASS;
  no global skill installation. Prioritizes varied male voices, college topics,
  real-world consequences, minimal text and no recycled mom/dog/phone/gym story.
- Focused story/provider-cache suite: 22 PASS. Python compilation and
  `git diff --check`: PASS. Live planner validation is recorded below.
- Live early drafts exposed weak formula wordplay, missing contact/landing
  actions, and lifting a frictionless cup with a side pinch. Those prompted
  stronger staging and humor checks. A v2 bus-stop draft passed its model audit
  but editorial review noticed a similar "ending up lower" gag; v3 supplies
  scoped history to the independent audit for semantic joke comparison too.
  The baseline sample 21 is recorded as user-rated potential, with the actual
  animation/caption feedback; generated drafts remain unreviewed.
- Three full alternatives can exhaust the old response allowance (an empty
  structured result was observed). The story CLI now explicitly requests a
  bounded 16,000-token maximum; the existing Claude adapter default stays 9,000.
  It validates the configurable limit and retains schema diagnostics, stop
  reasons, usage, and failed/interrupted run status. Interrupted one local
  validation run to apply this adjustment; no video regeneration was needed.
- Follow-up live work found the full-batch rewrite could still exhaust 16,000
  tokens (13,614 reasoning tokens in one observed response). Replaced that loop
  with three initial alternatives and at most two targeted repairs per candidate,
  followed by a fresh audit. Kept the completed provider drafts and reran them
  through the corrected validators rather than regenerating the same material.
  The notation gate now accepts mathematical subscripts/arrows such as `f_s`
  and `2v ⇒ 4F`, while continuing to reject prose labels and slogans.
- Novelty review now compares explicit comic expectations/reversals, not every
  sentence in a physics explanation. Reusing a mechanics principle is allowed;
  recycling the same comic goal and payoff is not. Added direct audit ownership
  checks and a test that a repaired candidate is grounded and re-audited.
  Linked retained guidance from both module and renderer AGENTS instructions.
- Added scoped planned-narrator rotation across four male stock voices already
  used by the auditions: Liam, Roger, Charlie and Callum. Avoids the last two
  planned leads and favors less recently used voices. CLI artifacts include the
  chosen ID with `planned_not_synthesized`; this is an authoring selection, not
  a production voice-rotation rollout or a claim that new audio was generated.
- The first bounded repair run withheld all three candidates with unresolved
  mechanics/staging issues. Resumed the actual provider-repaired drafts for
  the next validation, rather than substituting hand-written passing stories.
  Audits now explicitly separate blocking defects from optional polish and do
  not require a gag in every beat. Final live outcome is recorded below.
- Final live outcome: `real-world-stories-4` returned the 121-word
  "Breakfast to Class, Minus Friction" plan from actual Opus alternatives.
  A model audit missed the jar's cross-scene timing and extra caption directions;
  explicit editorial review corrected those, preserved the original draft and
  recorded the changes, then a fresh live audit passed. This is evidence that
  model audits still need editorial/visual review, not a claim of fully automatic
  physical correctness. Current artifact: `.local/story-engine-v2-audition/story-03.json`;
  `editorial-audit.json` and `editorial-usage.json` retain the final live evidence.
- Final plan was revalidated against the current schema and scoped history:
  approved structure, no detected recent-story repetition, matching fingerprint
  and stored history. It remains user-unreviewed. Planned narrator is Roger,
  distinct from the rendered sample's Liam; no new audio or animation is claimed
  for this plan. Added a deterministic guard against scene directions injecting
  caption text that is not in the spoken beat.
- Rechecked the final friction MP4 and all three SHA-bound technical/motion/pop
  reports against the current file; the gallery copy matches. The gallery now
  contains 22 samples, including a subsequently added sample 22; all existing
  media were preserved. Sample 21 remains available at `#friction-straight`.
  Final focused suite: 22 PASS; skill validation, compilation and diff checks PASS.


## Live Instagram branch phone installation — November 14, 2026

- Fetched `origin/adi-live-instagram-feed` at `251fc99` and created a detached
  worktree at `.local/iphone-build/adi-live-251fc99`; preserved the main working
  tree, its branch, and all unrelated edits. No merge or push.
- Reused the previous isolated native/dependency build; verified no package or
  lockfile changes between `adi-private-phone-feed` and the new branch. Installed
  the branch-pinned Python dependencies into the existing isolated probe venv.
- Configured only the existing Supabase URL and publishable key in the ignored
  mobile `.env`. Live Auth settings returned HTTP 200 with email login enabled.
- `npm run typecheck`, `npm test` (32/32), `npm run contracts:check`: PASS.
  Initial proxy test failed only because sandbox socket binding was denied;
  rerun with local networking passed. Entertainment tests: 19/19; experiment
  tests: 13/13. Provider/auth behavior in these tests is synthetic.
- Opened the branch's hidden-input login helper in Terminal. At this checkpoint
  there is no `.local/instagram-live/connection.json` or completed report.
  The earlier four-Reel import saved no reusable Instagram session.
- User explicitly approved ngrok forwarding app bearer tokens and personalized
  Reel metadata. Initial generic tunnel approval was rejected by automatic
  review; the explicit ngrok approval was subsequently accepted. Installed
  ngrok 3.14.0 was too old, so updated only a temporary copy to 3.39.13.
  Temporary tunnel is running with request inspection disabled, targeting
  loopback port 8000. Backend is not running until private login completes.
- Generated Hermes bundle from this worktree with `expo export:embed`, API feed
  selected, saved preview disabled. Verified the new HTTPS origin and rolling
  prefetch code are embedded and all four previous private Reel IDs are absent.
  Native package versions are unchanged, so reused a copy of the prior native
  shell, replaced bundle/assets, signed with the existing development identity.
  `codesign --verify --deep --strict`: PASS.
- `xcrun devicectl device install app`: PASS on the paired iPhone 15 Pro, bundle
  `dev.hackumass.studyfeed`. Artifact: `/private/tmp/hackumass-live-251fc99/Studyinyourfeed.app`.
- App launch was NOT executed: automatic approval review hit its usage limit.
  This was a review-service failure, not a finding that the launch is unsafe.
  User can open the installed app normally. Prepared an ignored manual backend
  launcher `.local/start-live-api.command` in the worktree.
- Remaining: complete private app/Instagram login, start API, verify missing/
  invalid bearer rejection through HTTPS, verify multiple live pages add unique
  clips, and observe physical iPhone playback/pagination/background recovery.
  No continuous live retrieval or phone playback acceptance is claimed yet.
  Mac/backend/tunnel must remain running for this temporary setup.

- Continuation: approval review recovered; the actual launch attempt reached
  iOS but failed with `Locked` because the phone was locked. User must unlock.
  A backend process is now waiting for the connection file, then will exec the
  existing live Uvicorn factory once, with loopback binding and no access log.

- User clarified they do not yet have an app account. Signup is enabled by
  live Auth settings and the installed bundle includes public auth config.
  The next user step is native Create an account, email confirmation, sign-in,
  then the same app credentials in the waiting private Instagram helper.


### 3D voxel story reference, template and new common-resource video — November 14, 2026

- User supplied a Minecraft-style stock-market MP4 and confirmed all three appeal
  factors: 3D models/camera work, causal storytelling and short white captions.
  Inspected local frames and on-device Apple Vision OCR (8 fps); no reference
  media was uploaded. Documented the contradiction → setup → ownership/transfer
  → expectations → reversal → return structure and the reference's limitations.
- Added `services/renderer/templates/voxel_story`: reference analysis, reusable
  authoring prompt, model-building instructions and the lake-adapter JSON schema.
  Added `services/renderer/experiments/voxel-story`: genuine Three.js geometry,
  original pixel textures, articulated block characters, perspective cameras,
  rods/lines/fish/crates, lake/village, frame-driven action and word-level white
  captions. Reusable actor/fish factories are exported from `src/World.ts`.
- New original topic: tragedy of the commons, including private incentives,
  shared depletion and the possibility of successful collective rules/monitoring.
  FAO and Ostrom sources accompany the template. Fish counts and compressed
  recovery time are illustrative, not a fisheries simulation. The user has not
  yet approved the sample's creative quality.
- Live narration: Brian, ElevenLabs `eleven_multilingual_v2`,
  113 aligned words in eleven shots; original quiet water/splash
  sounds. This is authored content, not a claim of live Claude story generation.
- Three.js 0.170.0 is pinned by SHA-256 in ignored local vendor storage with its
  MIT license. No JS lockfile or public format IDs changed. Decision 008 describes
  the proposed production integration and owner handoffs. New topics still need
  authored props/actions; changing narration alone is not general 3D generation.
- Commands actually run: `fetch_vendor.py`; `prepare.py` using the API venv with
  `PYTHONPATH=services/api`; `sound.py`; `run.py stills` (repeated after correcting
  syntax, mouth scaling and catch-line attachment); `run.py video`; `finalize.py`;
  `verify.py`; `preview.py`. Rendering used the existing reference-v7 image,
  non-root/read-only, network disabled, no application/provider credentials,
  4 CPUs / 4 GiB, PID/file/time limits. Nonfatal webpack cache EROFS warning.
- The first export check correctly rejected full-range `yuvj420p`; normalized
  range and reran verification against the actual final file. Final output:
  `.local/voxel-story/output/commons-lake/lesson.mp4`, 41.067s,
  720×1280 at 30 fps, H.264/yuv420p + AAC, peak -5.0 dBFS,
  mean -22.7 dB. Full audio/video decode, word timing bounds
  and 22 encoded inspection frames PASS. Inspected the encoded contact sheet.
  SHA-256: `5f268d0615f998bc76d27df1d1e5529dbca877783d6c72f94daa0f38227de68f`.
- Python compilation, Node syntax check, `git diff --check`, staged speech/camera
  identity checks PASS. Valid story accepted; malformed voice path, nonfinite
  camera, unexpected field and invalid scene order rejected before synthesis.
- Added sample 22 to `http://127.0.0.1:8787/#commons-lake`; three existing browser
  ratings remained visible. Template source archive:
  `.local/voxel-story/voxel-story-template.zip`. Generated media and reference
  analysis remain ignored/uncommitted. Physical-iPhone playback, hosted-storage
  publication and production-feed integration have not been tested/implemented.

- User reports successful phone app sign-in followed by Reels HTTP 502.
  Verified ngrok reports connection refused at 127.0.0.1:8000. The backend
  waiter is still alive, and no owner-bound Instagram connection or report
  exists yet. Thus this is an unstarted backend pending the Terminal Instagram
  connection, not evidence of failed app sign-in or live provider pagination.
- Final IAB playback evidence: played range covered 0–41.067s (the full file),
  readyState 4, no media error. Left the gallery tab available for user review.

## Live-feed pagination and native playback investigation — November 14, 2026

- User completed private Instagram connection and reported phone sign-in and
  initial live playback, followed by flash/blank videos and exhaustion at four.
  Backend started; local and ngrok feed requests without/with invalid bearer
  correctly return 401 AUTH_REQUIRED/AUTH_INVALID, replacing prior 502.
- Reproduced provider bug live: three query-cursor pages each contained the same
  four Reels (new unique counts 4, 0, 0), despite different provider cursors.
  POST-body continuation instead returned 4, 2, 7 unique clips. Applied a local
  fix in the isolated `adi-live-251fc99` checkout and added a behavioral provider
  regression simulating ignored query cursors. Restarted the phone API.
- Actual fixed catalog service returned six pages with 4, 2, 3, 5, 2, 3 new
  unique Reels (19 total), all with continuation. Only aggregate counts saved
  in `.local/fixed-catalog-pagination-check.json`; no raw provider responses.
- Fixed new-root deduplication scope locally: after the 30s retry window, an
  explicit reload resets traversal seen IDs. Retry within the window still
  replays the root, and duplicates within a traversal remain filtered. Added
  regression covering fresh root, duplicate next-page removal and old cursor
  rejection. Entertainment tests now 21/21 PASS. Latest root fix still needs
  API restart and simulator acceptance.
- Simulator signing was previously insufficient for SecureStore. A manual
  entitlement-only resign could not launch; incremental native Xcode build
  with CODE_SIGNING_ALLOWED=YES and simulator keychain entitlements succeeded.
  Installed copy from `/private/tmp/hackumass-live-simulator-xcode`. New live
  branch runs through localhost Metro; sign-in form is enabled, with no
  SecureStore entitlement errors on fresh startup. User asked to sign into
  simulator using the same app account; authenticated UI test remains pending.
- Flash/blank playback remains under investigation; no fix/acceptance claim.
  Changes are isolated local proposals for Adi's ownership; no main-tree mobile
  or entertainment files changed and no branch was pushed.

## Sample 22 acting revision and shared captions — November 14, 2026

- User approved the white captions, requested much stronger animation across
  formats, rejected fishing characters facing away from the lake, and authorized
  Codex plus optional GPT-6 Astra for reusable models to reduce Claude calls.
  Implemented this revision directly with Codex; zero additional Claude, Astra
  or ElevenLabs calls. Reused frozen narration/alignment. No Astra API integration
  is claimed. Original sample retained under `.local/voxel-story/archive/v1`.
- Extracted original procedural assets into voxel `src/ModelKit.ts` (articulated
  shoulders/elbows/hands, eyelids, fish/crates/textures). `Blocking.mjs` provides
  target-facing/shortest turns, dry-bank paths, phased fishing actions and unique
  catch identities. World staging now follows task targets, attaches rods to
  hand transforms, shows cast/lift/deposit and differentiated reactions, and uses
  lake-side cameras to show faces without turning actors away from their task.
  Corrected cropped framing and a face-obscuring lift after inspecting stills.
- Shared `src/PopCaptions.tsx` preserves the approved white single-word styling,
  speech alignment and restrained pop. Adopted by main dialogue/visual/guided
  lessons and voxel/friction/general audition renderers. Music-led math retains
  its equation treatment. Older MP4s require rerendering to adopt these changes.
- Added `services/renderer/ANIMATION_STANDARD.md` and updated retained direction,
  authoring/review skills and prompts: Codex-first asset reuse, task-facing acting,
  contact/support/continuity checks and inspection of every complete shot.
  Motion-review staging now includes all authored shots, including experimental
  `segments`; bounded to 48 shots. Clips aid inspection, not automatic approval.
- Commands/results: `node --test services/renderer/tests/*.test.mjs` — 64 passed;
  focused API pytest `test_motion_review.py test_provider_cache.py` — 13 passed.
  Node syntax checks, Python compilation and `git diff --check` passed. New
  geometric tests cover all seven facing targets and dry paths, shortest turns,
  unique fish transfers and two remaining fish. Fixed specialized review-label
  deduplication and numeric test tolerance before the passing reruns.
- Built offline `hackumass-renderer:reference-v8-captions` from installed v7
  dependencies with updated renderer sources (`docker build --network=none`).
  Rendered/inspected cached main dialogue and visual-explainer stills with it.
  Updated local image selection/defaults and recipe version 4.1.0 with shared
  caption digest. No paid content regeneration, service restart or deployment.
- Executed voxel `run.py stills`, `run.py video`, `finalize.py`, `verify.py`,
  `preview.py`; inspected 22 encoded frames and all eleven full-shot motion strips
  (16 clips staged). Final SHA-256:
  `c09f549a9ce6de41a849ade7963d0c9d077eae8bc8a12d347e67bd2613c9124d`.
  Export: 41.067s, 720×1280, 30fps, H.264/yuv420p + AAC, peak -5.0 dBFS;
  full decode and word bounds passed. IAB played 0–41.067s, readyState 4, no
  media error. Sample 22 is first in the local gallery, three ratings preserved.
- Executed friction-story-v2 `run.py stills`, `run.py video`, `finalize.py`,
  `verify.py`, `preview.py`; restored voxel-first gallery order afterward.
  Sample 21 now demonstrates the shared captions in a complete 2D export:
  44.8s, 720×1280, 30fps, H.264/AAC, full decode and caption bounds passed.
  SHA-256: `7e1e3010c3f2e1436878828657799db30b9de061b419851e14c066476bdf10e0`.
  Inspected caption stills; this was a caption update, not a new 2D acting pass.
- Updated source manifest and verified `.local/voxel-story/voxel-story-template.zip`
  (21 source files plus evidence; includes shared captions, model kit and standard).
  Generated MP4s remain ignored. New acting awaits user creative approval;
  physical iPhone playback and production-feed integration remain unvalidated.
  Authored motion and compressed fish recovery are not a physics/ecology simulation.

## Two new template trials — November 14, 2026

- User requested a presidential-election lesson in the 3D template, allowing 2D
  animation, then added a second new topic in the friction cartoon style with
  cleaner animation and the same approved captions. Created both, preserving
  existing samples, working-tree changes and public format contracts.
- Sample 23, `election-story` / `election-college`: original U.S. Electoral College
  story with fictional orange/teal candidates and three explicitly fictional
  equal-weight states. Reuses voxel `ModelKit.ts` directly through a read-only
  mount and shared `PopCaptions.tsx`. New civic plaza, ballot handling, distinct
  electoral-token transfers, candidate reactions and 2D vote/process diagrams.
  National Archives overview/allocation/FAQ checked live; source links and shot
  plan saved in the adapter README. Toy vote totals independently checked:
  orange 196 versus teal 104 popular; teal 10 versus orange 5 electoral.
- Sample 24, `spin-story` / `spinning-chair`: original vector room/character and
  swivel-chair action following friction-story-v2's everyday story direction.
  Fixed-length elbow solutions keep hands/weights connected; 240 Hz integration
  samples continuous rotation at 30 fps. Tucking halves illustrative total I and
  doubles omega while conserving L; floor torque smoothly stops rotation. Explicit
  spoken rewind is the sole intentional angle reset. OpenStax and SFU primary
  teaching sources checked. The model is normalized, not human biomechanics.
- Codex authored all models, motion, diagrams and scripts. No Claude/Astra calls.
  Synthesized 12 Roger segments and 10 Charlie segments using existing ElevenLabs
  server configuration; froze/cache-reused voice throughout animation revisions.
  Initial sandbox networking failure was retried successfully with approved
  network access. No reference video or private course material was uploaded.
- Stills were inspected and repaired before full exports: widened election
  framing to retain leads/state platforms, moved captions clear of action,
  distinguished Maine/Nebraska token groups, and corrected the 2D elbow branch
  that crossed through the torso/head. Both use the unchanged white word-caption
  component. Old unrelated films were not rerendered.
- Commands actually run for both adapters: `prepare.py` (API venv with
  `PYTHONPATH=services/api`), isolated `run.py stills`, `run.py video`, `finalize.py`,
  `verify.py`; original quiet foley generated locally and reproducible `sound.py`
  retained. Targeted election stills used `--still-indices` after camera repairs.
  Docker: existing `reference-v8-captions` image, non-root/read-only, no network
  or app/provider credentials, 4 CPUs/4 GiB, PID/file/time limits. Nonfatal webpack
  read-only cache warning; no new dependencies, service or lockfile edits.
- `node --test services/renderer/tests/*.test.mjs`: **68 passed**, including four
  new behavioral checks for winner-take-all transfer accounting, connected limb
  lengths, conserved L/changed speed and energy, continuous rotation and complete
  braking. Both closed story schemas accepted valid scripts and rejected four
  malformed variants each. Node syntax, Python compilation and diff whitespace
  checks passed. `story.schema.json` files exported from the actual validators.
- Final 3D export: `.local/election-story/output/election-college/lesson.mp4`,
  **57.045s**, 720×1280, 30fps, H.264/yuv420p + AAC; peak -5.0 dBFS, mean -21.7 dB.
  SHA-256 `f9899b233dd3618db26bc2aa14e6fbcfac54f3bfd68b3a53a0230cded69bd6ec`.
  Final 2D export: `.local/spin-story/output/spinning-chair/lesson.mp4`, **41.6s**,
  same dimensions/codecs; peak -5.0 dBFS, mean -21.5 dB.
  SHA-256 `73251442e45c43cb106992826b734218f4e82e378f9b3e8828964f825f12c634`.
  Full decodes, caption bounds and encoded contact-frame inspection passed
  (36 election frames, 30 spin frames; beginning/midpoint/end of every shot).
  Motion-review clips also staged for every shot; numerical tests are not a
  substitute for creative approval.
- `election-story/preview.py` staged both into the existing gallery as 23 and 24;
  24 samples and three prior ratings are visible. Source archive verified at
  `.local/template-trials/template-trial-sources.zip` with 30 source files and a
  SHA-256 manifest; no credentials, narration cache or generated MP4s in source.
  Generated artifacts remain ignored. Physical iPhone playback and production
  integration are not claimed; both new creative treatments await user review.

### Authenticated simulator acceptance and updated phone build — November 14, 2026

- User signed into the native iPhone 17 / iOS 26.3 simulator. Restarted the live
  API with both pagination and root-dedup fixes. Live authenticated UI initially
  expanded from four to ten clips with the original player implementation.
- Locally changed FeedScreen to keep one VideoView mounted outside recycled
  FlatList cells while switching the two buffered players; guarded late native
  status/playing events by player owner. This targets a suspected native surface
  handoff race. The original intermittent flash/blank was not reproduced in the
  simulator, so its root cause is not conclusively established.
- Reloaded Metro with the modified player and traversed 12 real Instagram Reels
  using Next clip. All 12 displayed video frames; pagination expanded the queue
  4 → 6 → 11 → 13 → 16. Sustained changing frames and visible watch time were
  observed, including over 40 seconds on clip 12. No blank-video failure or page
  error appeared in this run. CUA drag attempts toggled pause rather than moving
  the feed; touch-swipe behavior is not claimed verified by this automation.
- Navigated to The lab and back; playback resumed visibly. Sent app home using
  Simulator Cmd-Shift-H, then simctl launch; same process resumed video. Used
  simctl terminate/launch for cold start: secure app sign-in persisted, a new
  four-item root batch loaded and played. This validates fresh root loading,
  not an infinite-duration stream or uninterrupted upstream availability.
- Validation already run against this patch: 21 entertainment tests, 32 mobile
  tests, mobile typecheck PASS. git diff --check PASS. No contract changes.
- Exported modified iOS JS/assets with expo export:embed, signed the existing
  matching native shell, and codesign --verify --deep --strict passed using
  the system trust store (sandbox-only verification could not access trust).
  devicectl installed dev.hackumass.studyfeed successfully on the paired iPhone.
  Physical playback of this latest build still needs user observation.
- Patch for Adi integration is retained at the isolated checkout's
  `.local/live-feed-fixes.patch`; four source/test files are locally modified.
  No commits or remote pushes; root mobile/entertainment implementation untouched.
  API, Metro and the approved temporary ngrok tunnel remain running on this Mac.
- Final physical-device launch request was denied because the iPhone is locked.
  Installation succeeded; user can unlock and open Study in your feed normally.

- Final IAB playback checks completed: sample 23 played 0–57.045s and sample 24
  played 0–41.6s; both readyState 4, no media errors. Gallery left available.
  Motion review staged 17 election clips and 15 chair clips; inspected key action
  strips in addition to every-shot encoded frames. User then requested the full
  current template inventory; inspected four main manifest directories, voxel
  and cartoon adapters, the 19-style audition catalog and all 24 gallery records.
## déclic design and app-branch integration — November 14, 2026

Implemented the newer v2 déclic branding from the user-supplied ZIP in isolated
`integration/declic-app` (`.local/declic-app`). All current remote branch tips are
ancestors after merge `bbb3481`; original uncommitted video/renderer work is intact.
Added licensed bundled fonts, app icons, welcome/auth UI, purple/coral feed actions,
Profile collections and playback settings, and authenticated academic profile UI.
No existing v1 fields or application identity changed.

Verification and exact distinctions: [DECLIC_VERIFICATION.md](../DECLIC_VERIFICATION.md).
Typecheck, 36 mobile tests, contract check, iOS/web export, 86 shared API/curriculum
checks and 22 Instagram checks passed;
7 real-database tests skipped. Live provider check retrieved 6 unique Reels over
2 pages. Browser UI playback and navigation were exercised with fixture media.
Native automation is awaiting dismissal of a stuck Simulator menu; no physical
phone or redesigned live native playback claim is made.

[Proposed API/storage follow-up](../decisions/009-declic-ui-api-storage.md) records
owner-scoped collections/preferences, connection health, truthful progress,
mixed feed/quiz UI, private sharing, runtime assembly and optional provider deps.
Session-only Clicked/Saved state is capped and cleared on sign-out. No migrations,
production deployment, provider credential collection or private media commits.

User-reported Reels issues addressed: POST-body provider cursor, continuation and
leftovers retained on reload, bounded session deduplication, earlier page prefetch,
two stable preloaded media surfaces, no loading flash for ready buffers, bounded
transient API retries, and whole-frame Fit/Fill control. Browser checks confirmed
failed-clip recovery and watched clips excluded after feed remount. The loopback
API now runs this integration on port 8000; Expo preview runs on 8094.

## Full application consolidation — November 14, 2026

Worktree `integration/e2e-app` combines the preserved learning/video work, déclic
app, Amogh curriculum, and Adi's live Instagram implementation. PR #1 merged the
learning foundation to main after recorded review. The follow-up integrates the
runtime, encrypted per-user Canvas PAT and Instagram sessions, Gemini lesson/quiz
preparation and semantic topic bindings, durable concurrent queues, private media
publication, and the mobile mixed feed. See `docs/RUN_DEMO.md` and decision 010.

Separate agent reviews found and fixed disconnect/publication races, stale quiz
revisions, cross-process academic snapshot overwrite, failed-job retry, global
Instagram diagnostic-stream corruption, and mobile swipe/watch/quiz ordering.
These are agent reviews, not independent human approval. All observed branch
implementation tips are included; the old dirty iPhone checkout remains intact.

Cloud evidence: Atlas ping/migrations and private Supabase bucket verification
passed. Disposable synthetic Supabase users exercised password login, refresh,
owner-authenticated API routes, feed session/page, preparation status and 401
rejection. Test sessions were revoked and test accounts/app rows removed.
A real HTTPS browser run exercised login, empty feed, reload/session restoration,
Courses provider/preparation status and logout with no page errors. No private
student sources or provider credentials were committed.

At 390×844, a separate synthetic-provider browser run exercised first→second video
playback with one active player, quiz playback pause, wrong-answer unlock, event
flush before quiz gate, PAT form, saved clip/profile navigation and tab restoration.
Screenshots are local under `.local/mobile-verify`; they are not provider evidence.
Mobile Node 24 typecheck and 40 tests passed; renderer 68 tests passed. The initial
full backend real-Mongo run passed 353 tests with 8 separately configured tests
skipped; the remaining auth/curriculum group subsequently passed 20 tests. Later
review fixes have additional focused tests; final consolidated totals follow.

Live limits: no Gemini key was supplied; `.env.gemini.example` and ignored
`.env.gemini.local` are prepared. Students enter Canvas PATs in-app. Adi's latest
real Instagram attempt failed `ClientNeedsUpgradeError` with zero pages; the
integration surfaces this condition and does not claim successful fresh login.
Physical iPhone playback and real Canvas→Gemini→feed remain unverified. Existing
G4 recommendations are the demo baseline; G7 learned policies remain post-demo.

Consolidated check: `API_TEST_MONGODB_URI=... MONGODB_TEST_URI=...
VIDEO_TEST_MONGODB_URI=... services/api/.venv/bin/python -m pytest services/api -q`
passed **402 tests, zero skipped**, against the disposable local replica set.
Node 24 mobile typecheck, 40 tests, and generated contract consistency passed;
renderer tests passed **85**, including trusted semantic-diagram geometry and
malformed-pack rejection. The new generic visual strategy preserves all content,
frame and media checks. Live generation observations are recorded separately below.

Cost correction: the user requested lower provider spending. Stopped additional
paid live probes, changed the default video model from Opus to Sonnet, capped
Claude stage calls at six per job (previously forty), and paused the local video
worker via VIDEO_GENERATION_ENABLED=false. The existing final diagram probe is
already past all model calls and may finish CPU rendering/storage without new
Claude calls. No background generation worker was started for student jobs.

Final cost-control head verification: **403 backend tests passed, zero skipped**
with all three disposable Mongo test settings enabled. The separate agent review
of commit `6e11318` found no blocking issue in the narrated demo path. Mobile
remains 40 passing tests and renderer 85. No live provider calls were used for
this final test run.

## Animated-shorts-inspired lake direction — November 14, 2026

Implemented a local source revision after the user approved adapting
https://github.com/mromidev/claude-animated-shorts. The user subsequently instructed
"no testing just yet tho". **No tests, builds, renders, previews, media checks or
provider calls were run for this revision.** Earlier passing results and exported
MP4s do not validate these edits. No new creative approval has been recorded.

Changes under `services/renderer/experiments/voxel-story/src`:
- `ShotDirection.ts`: original multi-key plans for all eleven lake beats;
  deterministic smootherstep sampling, explicit cuts, FOV/target interpolation,
  bounded cue-word lookup within each narration segment, caption-placement helper.
  Exported interfaces: `DIRECTION_VERSION` (`voxel-cinematic-v3`), `wordCue`,
  `lakeShotPlan`, `sampleShot`, `lakeCaptionTop`.
- `Acting.ts`: opt-in face geometry and absolute-time expressions; exports
  `addExpressionRig` and `poseExpression`. Original shared ModelKit consumers
  are unaffected. Mouth sizing now uses the box's actual dimensions in this scene.
- `World.ts` / `Root.tsx`: wire shot plans to staged word alignment and physical
  catch/release timing, add a neighbor's glance and staggered disappointment,
  warmer key/cool ambient lighting with gradual horizon-matched fog color,
  and lower placement of the existing white word captions.

Updated template authoring instructions, revision README and reusable-asset
inventory. New code is original; no upstream media or source was copied. No new
dependencies, public schema fields, production wiring, or fixtures were introduced.
The existing synthetic common-pool lake storyboard and staged narration remain
the input; visual-only rendering can reuse the pack without preparing voice again.
CodeGuard applied: scene selection remains authored, cue text is compared as data,
and no credentials, executable input, networking or package installation were added.

Commands actually run were read-only source/status inspection (`git status --short`,
`cat`, `rg`, `head`, `tail`); edits used `apply_patch`. Pending at the user's request:
type/build checks, deterministic frame/pose checks, full stills and motion review,
camera occlusion and caption clearance, encoded audio/video verification, and
creative review. No gallery refresh, publication or iPhone playback was attempted.

## Live phone installation and course-evidence correction — November 14, 2026

Installed and launched a signed standalone Release of main `1ef4b69` on the user's
iPhone 15 Pro. A physical screenshot shows authenticated real Instagram media in
the native feed. This proves native rendering, not sustained swipe/audio/background
or quiz acceptance. Build details, screenshot, and the isolated Xcode 26 Swift
compatibility patch are private local artifacts under `.local/iphone-build/main-1ef4b69`.
The app uses the integrated HTTPS API; no server secrets are bundled.

Root `.env` now supplies Gemini. Live probes verified configured model access,
one schema-valid grounded synthetic quiz, and a normalized 768-dimensional semantic
embedding. The student connected Canvas and Instagram in the actual app: four
courses imported and six Instagram clips were initially saved. No tokens or raw
course documents are included in this status file.

The user authorized five live videos. The first batch exposed administrative
assignment topics rather than conceptual lessons and was cancelled before any
publication. Diagnosis found 14 selected PDFs without persisted text because
`pypdf` was absent from runtime dependencies. Added pinned PDF extraction, cache
retention on unchanged reimport, and correct file-update invalidation. Added
teaching-source and output gates, refusal support, stale-revision protection, and
matching lecture references. The corrected live reimport is running; five ready
videos and live quiz acceptance are not yet established.

Instagram import now clears only the owner's prior account catalog. Explicit
playback retry renews revoked/expired URLs using the encrypted saved session,
with throttling and connection/version fences. Focused mocked-provider tests ran
against disposable Mongo. Consolidated command with all three Mongo test URI
settings enabled: `services/api/.venv/bin/python -m pytest services/api -q` —
**465 passed, zero skips**. Independent PDF cache and worker-allowlist reviews
found no blocking issue. No provider calls were used for automated tests.

Follow-up live import retained 15 text-bearing files but revealed syllabus learning
outcomes and old exam selection. Retrieval now reserves three of its five file
reads for lecture/chapter material. Bounded source-quoted concept recovery fills
missing grounded units without inventing deadlines or exam scope. Revision three
produced plans across all four courses. Outcome-only facts and uncertain PDF
notation are rejected; exact authorized citation tags stay out of narration and
quiz text. One observed corrupted-symbol quiz was quarantined. Obsolete/invalid
queued jobs were cancelled, preserving the active five-job batch.

The semantic cache now reuses identical compatible fact sets even when headings
or goals differ. Final consolidated API verification after these changes:
**494 passed, zero skips**, with the disposable local Mongo configuration and no
provider calls. The first two accepted live videos reached full rendering after
content/frame checks; a rejected causal diagram is being replaced with comparison
visuals. Private storage publication and native quiz verification remain pending.
