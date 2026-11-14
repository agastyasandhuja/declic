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
