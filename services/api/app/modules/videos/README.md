# Local educational video generation

Four formats are available: `dialogue_gameplay`, `visual_explainer`,
`space_explainer`, and music-led `math_explainer`. New Brief objects default to
`reference_v3` / `3.0.0`; historical v1/v2 packs remain readable. Remotion renders
frames; the Python harness plans, retrieves assets, synthesizes audio and verifies.

Video planning and review default to **Opus 5.5** (`VIDEO_CLAUDE_MODEL=claude-opus-5-5`).
The generic `CLAUDE_MODEL` no longer controls video agents. Reference v3 adds image
content deduplication, actual candidate-image selection, four distinct space scene
types, dark dialogue diagrams, and a sampled-frame review before full rendering.
A rejected review stops with a local report; it does not silently approve a draft.

Math currently supports 2–3-dimensional matrix multiplication only. It computes
exact arithmetic in Python and checks it again in the renderer. Source matrices
remain stable while colored factors move into a dot product, then into a result
cell. The agent chooses a hook, payoff and licensed instrumental track. It does not
reuse the reference soundtracks. Music attribution is in CREDITS.txt and the manifest; include it when sharing.
The minimal math canvas has one title, large matrices and moving numbers only.
Its 2×2 example is 21 seconds; math allows 20–60 seconds, speech formats 30–60.

```sh
PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.videos.cli generate --brief fixtures/learning/revised-finance-brief.json --format visual_explainer --output .local/video-runs/revised
PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.videos.cli generate --brief fixtures/learning/revised-linked-list-brief.json --format dialogue_gameplay --output .local/video-runs/revised
PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.videos.cli generate --brief fixtures/learning/revised-cosmic-web-brief.json --format space_explainer --output .local/video-runs/revised
PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.videos.cli generate --brief fixtures/learning/matrix-math-brief.json --format math_explainer --output .local/video-runs/revised
```

`--fixture --prepare-only` on the math example uses a deterministic direction and
a synthetic tone, makes no model/music request, and is explicitly marked fixture.
Review the actual videos as well: sampled frames do not verify motion or audio.
No upload or iPhone integration is implied. See [decision 006](../../../../../docs/decisions/006-video-quality-and-math-template.md)
and the dated status evidence.

## Earlier implementation details

# Video generation runtime

Three local formats are implemented: `dialogue_gameplay`, `visual_explainer`, and
`space_explainer`. New `reference_v2` briefs use continuous shot-driven narration:
one active character over gameplay, image-led narration, or layered spatial animation.
General approved-fact subjects use `trace_kind=none`; linked-list reversal retains
its trusted semantic trace. Other algorithms still need appropriate validated diagrams.
Character movement is a subtle audio-driven bounce and entrance, not phoneme lip sync.
The earlier five-beat `guided_v1` presentation remains available.

## Setup and local runs

From the repository root, with Docker Desktop running and host FFmpeg installed:

```sh
docker build -t hackumass-renderer:0.1 services/renderer
cd services/api
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-video.txt
```

Merge `.env.video.example` into the repository-root `.env` without overwriting any existing
configuration. Set `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY` and the three voice IDs.
The local CLI loads root `.env` first and `services/api/.env` as a fallback;
`--env-file` overrides the primary path. Deployed workers inject secrets themselves.
All `.env`, `.local`, and generated MP4/audio files are excluded from Git.

Put `parkour.mp4`, `peter.png`, and `stewie.png` in `.local/video-assets` at repository
root. An optional `stewie-standing-v2.png` supersedes the bike pose only in reference
presentation; it is a generated local asset, not committed. Downloaded artwork provenance is in `docs/VIDEO_VERIFICATION.md`.

Run these commands from `services/api`:

```sh
.venv/bin/python -m app.modules.videos.cli preflight
.venv/bin/python -m app.modules.videos.cli voices
.venv/bin/python -m app.modules.videos.cli generate --brief ../../fixtures/learning/linked-list-brief.json --custom-scene --output ../../.local/video-runs/linked-list-live
```

`generate` defaults to both original formats using the reference linked-list brief.
The command above explicitly chooses the earlier guided brief. `--custom-scene` asks Claude to write the
visual-explainer JSX phase animation. The root owns the linked-list diagram and
code, and clips generated visuals to the badge band so they cannot obscure
teaching content, title, captions or narration. Code compiles only in the isolated
container. Omit the flag to use
the authored trace renderer. Stock substitutes are configured locally as Roger
(`CwhRBWXzGAHq8TQ4Fs17`), Daniel (`onwK4e9ZLuTAKqWW03F9`), and Alice
(`Xb7hH8MSUJpSbSDYk0k2`). Set `VIDEO_VOICE_DISCLOSURE` to identify substitutes.
These are not claimed to be Peter or Stewie impersonations.

Offline macOS smoke test (synthetic scripts, macOS `say`, estimated timing):

```sh
.venv/bin/python -m app.modules.videos.cli generate --fixture
```

Outputs include a generation manifest, frozen storyboard, timed lesson, individual
speech/cache metadata, VTT/word captions, representative frames, and MP4. `--preview`
renders 540×960 and is never publishable; normal output is 1080×1920. `--prepare-only`
stops before Docker. `render` reruns an existing pack; `validate` checks its final
output and refreshes the manifest. Neither means human or iPhone approval.

## Durable jobs and API integration

`enqueue` creates both jobs; `worker` claims and processes one job. Both accept
`--output PATH` as the artifact root and `--fixture` for the explicit local fake.
Add `--mongodb` to use `MONGODB_URI`/`MONGODB_DATABASE` instead of the local SQLite
fake. MongoDB must support transactions (Atlas or a replica set).

```sh
.venv/bin/python -m app.modules.videos.cli enqueue --fixture --output ../../.local/video-jobs
.venv/bin/python -m app.modules.videos.cli worker --fixture --output ../../.local/video-jobs
```

Production callers use `VideoService.request_generation(actor, request_id, format,
generation_recipe(...))`. The injected academic resolver must implement
`resolve_generation_brief(actor, request_id, format)` and verify ownership, source
access, and academic revision. There is no mobile endpoint accepting arbitrary
briefs or JSX. The CLI is a trusted local administrative interface.

Mount `create_router(service)` from `router.py` with core's `domain_routers` argument.
Pass `FeedVideoReader(service)` as core's `videos` argument. It implements
`list_variants`, `get_variant`, and `resolve_playback` and only returns accessible
ready catalog records. Authentication is the shared core `CurrentUser` dependency.
These seams are implemented; main.py has not been changed behind the other chat.

Atlas collections are `video_generation_jobs`, `video_variants`, and `video_outbox`.
`initialize()` installs uniqueness indexes. Core's `app.core.migrate --apply
--include-videos` runs this after its API migration; that ordered setup was tested
twice against a disposable local replica set. The video outbox is a separate producer
collection; the shared worker integrator must register its consumer. Until then,
the feed adapter reads current ready variants directly. Candidate jobs remain
owner-scoped until generic lineage is approved; approved generic variants can be
reused across owners. Video collection validator drafts and outbox consumption
remain integration work.

## Review and publication

Generation ends at `awaiting_review`/`validating`, never automatic readiness.
An operator reviews content, frame readability, speech synchronization, and asset
provenance, then creates a local JSON review with `video_sha256`, the exact
`artifact_digests` map from the generation manifest, and true booleans for
`content`, `visuals`, `audio_sync`, `assets`. Generic publication additionally
requires `generic_lineage: true`. Do not set these without actually reviewing.

```sh
.venv/bin/python -m app.modules.videos.cli publish --mongodb --job-id JOB_ID --owner OWNER --review /absolute/review.json --output ../../.local/video-jobs
```

Requires server-only Supabase service-role configuration and an existing private
`VIDEO_STORAGE_BUCKET`. Uploads are hash-addressed, downloaded and digest-verified
before the Atlas catalog/job/outbox transaction. Fixtures and previews cannot
publish. Private playback is authorized in Atlas before a 15-minute URL is issued.
Unreferenced uploads from failed publication remain private; orphan garbage
collection is not yet implemented. No hosted upload has been tested here.

## Bounds and verification

Three structured-output attempts per stage, 24 Claude turns, two measured-duration
revisions, two scene repairs, and two worker attempts. The pipeline checks a
20-minute deadline (30 minutes for space) at stage/provider boundaries; an in-flight provider request can
run to its own timeout. Rendering has an 1100-second cap (1600 seconds for authored space) and polls
cancellation. Space uses four capped CPU cores; other formats use two. Memory,
process, filesystem and network restrictions are unchanged.
Worker heartbeats fence stale/cancelled workers. Reusing a workspace preserves
spent turn/repair budgets; start a new workspace deliberately for a fresh recipe.

```sh
.venv/bin/ruff check app/modules/videos
.venv/bin/python -m pytest app/modules/videos/tests -q
VIDEO_TEST_MONGODB_URI='mongodb://localhost:27019/?directConnection=true&replicaSet=rs0' .venv/bin/python -m pytest app/modules/videos/tests -q
```

See `docs/VIDEO_VERIFICATION.md` for actual results and remaining live checks.

## Teaching and reference styles

`guided_v1` requires hook, prediction, reveal, retrieval and feedback beats, with
measured two- and three-second thinking pauses. The supplied reference videos call
for a different presentation: `reference_v2` uses six or more timed shots, continuous
narration, shorter word captions and source-relevant imagery. Engagement and learning
uplift remain unmeasured; these are versioned production heuristics.

From the repository root:

```sh
PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.videos.cli generate --brief fixtures/learning/reference-linked-list-brief.json --format dialogue_gameplay --output .local/video-runs/reference-demo
PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.videos.cli generate --brief fixtures/learning/reference-leatherback-brief.json --format visual_explainer --output .local/video-runs/reference-demo
PYTHONPATH=services/api services/api/.venv/bin/python -m app.modules.videos.cli generate --brief fixtures/learning/reference-cosmic-web-brief.json --format space_explainer --output .local/video-runs/reference-demo
```

`--storyboard-feedback PATH` adds explicit editorial feedback to the generation
identity. `--fixture --prepare-only` uses synthetic storyboards, macOS voices and
clearly marked color-field image placeholders with zero image-provider requests.
`--format both` still means the original two formats; space is selected explicitly.
`--custom-scene` applies only to guided presentation. Reference scenes use the
trusted renderer's shot API. Rebuild Docker after changing renderer source.

`VIDEO_BACKGROUND_MODE=auto` selects gameplay for reference dialogue and concept-only
for other presentations. Explicit `gameplay`/`concept_only` overrides remain supported.
The character format no longer adds a persistent title, speaker tags or progress bar.

Claude proposes public-topic image requests, selects returned candidate IDs, then
inspects downloaded raster images and plans per-shot focal points, wide views and
close-ups. Search uses NASA and Openverse. Downloads allow only HTTPS on
`images-assets.nasa.gov`, `upload.wikimedia.org`, and `live.staticflickr.com`, with no
redirects, bounded bytes/pixels, raster magic checks and JPEG normalization. The
renderer sees only staged files and retains no network or app credentials. Search
has bounded transient retries; failed downloads or visual checks can choose another
candidate up to three times. Unresolved image failures block the generation job, not
entertainment playback. Metadata and embedded image text remain untrusted.

`image-candidates.json`, `image-review*.json` and `image-selection.json` retain source,
license, creator, hashes and framing. Automated reviews remain fallible: inspect the
rendered crop, source claims and licensing before publication. Content-review records
are bound to the storyboard digest, so editing a cached script requires a new review.
The supplied generic source examples use [NOAA leatherback facts](https://www.fisheries.noaa.gov/species/leatherback-turtle)
and [NASA large-scale structures](https://science.nasa.gov/universe/galaxies/large-scale-structures/).

See [decision 005](../../../../../docs/decisions/005-reference-driven-video-templates.md),
[research and evaluation](../../../../../docs/VIDEO_ENGAGEMENT_RESEARCH.md), and the
latest local evidence in [Agastya's status](../../../../../docs/status/AGASTYA.md).
