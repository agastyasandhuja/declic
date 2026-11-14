# Video generation runtime

The initial lesson implementation supports singly linked-list reversal and two
formats: `visual_explainer` and `dialogue_gameplay`. The latter uses user-provided
Minecraft footage and Peter/Stewie artwork. Character movement is currently an
audio-amplitude mouth overlay and bounce/glow calibrated to the downloaded art,
not phoneme-accurate lip sync. Other concepts and the
three reserved formats need their own validated semantic traces/templates.

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
root. Downloaded artwork provenance is in `docs/VIDEO_VERIFICATION.md`.

Run these commands from `services/api`:

```sh
.venv/bin/python -m app.modules.videos.cli preflight
.venv/bin/python -m app.modules.videos.cli voices
.venv/bin/python -m app.modules.videos.cli generate --custom-scene --output ../../.local/video-runs/linked-list-live
```

`generate` defaults to both formats. `--custom-scene` asks Claude to write the
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
20-minute deadline at stage/provider boundaries; an in-flight provider request can
run to its own timeout. Rendering has an 1100-second cap and polls cancellation.
Worker heartbeats fence stale/cancelled workers. Reusing a workspace preserves
spent turn/repair budgets; start a new workspace deliberately for a fresh recipe.

```sh
.venv/bin/ruff check app/modules/videos
.venv/bin/python -m pytest app/modules/videos/tests -q
VIDEO_TEST_MONGODB_URI='mongodb://localhost:27019/?directConnection=true&replicaSet=rs0' .venv/bin/python -m pytest app/modules/videos/tests -q
```

See `docs/VIDEO_VERIFICATION.md` for actual results and remaining live checks.
