# Agastya status

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
