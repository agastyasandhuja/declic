# Video verification — 2026-11-14

## Observed results

The live Claude + ElevenLabs local path subsequently passed with the root `.env`.
Claude generated both scripts and the explainer's phase-animation JSX. ElevenLabs
generated timestamped speech using Roger (Peter), Daniel (Stewie), and Alice
(narrator), as approved stock substitutes. Validated live speech was cached and
reused during visual revisions; those revisions did not synthesize it again.

| Live format | Duration | Final path relative to repository root |
|---|---:|---|
| visual_explainer | 48.704 seconds | `.local/video-runs/linked-list-live-v2/visual_explainer/output/lesson.mp4` |
| dialogue_gameplay | 54.571 seconds | `.local/video-runs/linked-list-live/dialogue_gameplay/output/lesson.mp4` |

Both exports are 1080×1920, 30fps, H.264/yuv420p, AAC48k, with progressive-playback
metadata. Loudness measured -16.77/-16.31 LUFS and true peaks -3.96/-3.98 dBFS
(explainer/dialogue). Last-word timestamps leave 0.310/0.325 seconds to the final
frame. Representative first/middle/final frames were inspected, including correct
final arrows, active/idle mouth overlays, readable captions and title boundaries.
This is frame inspection and automated timing/media verification, not physical
iPhone or independent perceptual audio approval.

Earlier freeform model diagrams were rejected for null-arrow errors and preserved
with failed visual-review notes. The final `trusted-trace-2` API keeps the tested
linked-list diagram/code in the root and clips Claude's presentation to the phase
badge band. Arbitrary model-authored diagram geometry is not claimed as validated.
The live dialogue adds amplitude-driven mouth overlays calibrated to the downloaded
art, plus bounce/glow. This is stylized speech movement, not phoneme lip sync.

Final renderer images: explainer
`sha256:839b08efa823c29da707b3e10ac4d0581ec51a8701a08e455b6dca3864c78d33`;
dialogue `sha256:e18139c89dbfb8db33d19a5ec067b66019666ae8db3c34eafa0b68af0208a368`.

### Earlier offline fallback exports

Two local linked-list-reversal fixture videos rendered successfully through the
Docker broker. Both are 1080×1920 H.264/yuv420p, AAC at 48 kHz, 30 fps, within the
30–60 second acceptance window. Final media checks passed:

| Format | Duration | Local output under `.local/video-runs/linked-list/` |
|---|---:|---|
| visual_explainer | 44.245 seconds | `visual_explainer/output/lesson.mp4` |
| dialogue_gameplay | 44.651 seconds | `dialogue_gameplay/output/lesson.mp4` |

Representative intermediate/end frames were inspected. They show pointer reversal,
code highlighting (explainer), captions, Minecraft footage and character artwork
(dialogue). The gameplay sample includes camera falls and transitions; selecting
an uninterrupted approved parkour interval remains an editorial improvement.
Character animation currently bounces/glows with speech amplitude; there is no
mouth rig. The fixtures use macOS voices and estimated caption timestamps.
They are explicitly labeled fixtures and cannot be published by the service.

The videos and frames are not committed. `generation-manifest.json`, `quality.json`,
and per-artifact SHA-256 hashes are alongside each output.

## Commands actually run

- `docker build -t hackumass-renderer:0.1 services/renderer`: passed. Local image
  `sha256:9dd5aea21a0fe26eb37d45bb025870ec8366c861b279cfdbfe344d1cfd31a252`.
- Both CLI `generate --fixture --format FORMAT` commands: passed after fixing
  Docker Desktop tmpfs extraction, full-range H.264 normalization, and reducing
  browser concurrency/cache/thread usage to stay within the sandbox limits.
- CLI `validate` for both final outputs: passed.
- Renderer `npm test`: 7 passed. `npm audit --omit=dev`: zero vulnerabilities.
- Video `ruff check`: passed.
- Video pytest including a disposable MongoDB 7 replica set: 28 passed at this
  checkpoint. This verifies the MongoDB adapter locally, not hosted Atlas.
- The same tests without the MongoDB env: 24 passed, 4 explicitly skipped.
- Runtime Docker isolation probe: passed non-root/read-only/no-host-secret,
  no-Docker-socket/no-external-network, PID/memory/capability restrictions.
- CLI durable enqueue smoke test: both formats created distinct queued jobs.
- Core `apply_ordered(..., include_videos=True)` ran twice on an isolated local
  MongoDB database: both migration records and video indexes verified. Disposable
  database and container were removed after testing.
- Live provider schema checks exposed overlong scripts and a forbidden narrator
  role in dialogue. Errors/prompt contracts were clarified; duration repair and
  speaker-only validation then passed. Private diagnostic artifacts were retained.

The test suite covers invalid semantic traces, cue/character timestamp errors,
scope-separated caches, concurrent enqueue, retries/fencing/cancellation,
transaction rollback, ready/outbox atomicity, storage digest verification,
sidecar review binding and unauthorized playback signing. Provider tests use
HTTP mocks; the separate live runs above provide actual provider validation.

## Assets and voice selection

- User-supplied `Downloads/minecraft parkour.mp4` was copied to
  `.local/video-assets/parkour.mp4` (original preserved). Approximately 388 MB,
  600.073 seconds, 1920×1080 at 60 fps. The selected render interval is muted,
  converted to 30 fps and portrait-cropped; source hash/interval are recorded.
- Peter artwork: [Wikipedia character page](https://en.wikipedia.org/wiki/Peter_Griffin),
  image `https://upload.wikimedia.org/wikipedia/en/c/c2/Peter_Griffin.png`.
- Stewie artwork: [Wikipedia character page](https://en.wikipedia.org/wiki/Stewie_Griffin),
  image `https://upload.wikimedia.org/wikipedia/en/0/02/Stewie_Griffin.png`.
  These are downloaded character images for the requested local demo, not an
  assertion of unrestricted redistribution rights. Asset approval remains pending.
- In the signed-in Agastya ElevenLabs profile, exact Peter Griffin search returned
  no match. Stewie search returned “Stevie – The Living Cartoon,” not verified as
  Stewie. User approved stock substitutes. Official My Voices copy-ID controls
  verified Roger `CwhRBWXzGAHq8TQ4Fs17`, Daniel `onwK4e9ZLuTAKqWW03F9`, and Alice
  `Xb7hH8MSUJpSbSDYk0k2`; configured respectively for Peter, Stewie and narrator.

## Remaining acceptance checks

Claude scripting/review, constrained JSX generation, and ElevenLabs timed speech
have now been exercised live. No hosted Atlas,
Supabase upload/signing, end-to-end academic binding, mobile feed or physical
iPhone playback is claimed. Live provider outputs must be reviewed before ready
publication. Shared core registration, ordered database migration assembly,
video-outbox consumption and orphan-upload cleanup remain integration work.
The ordered index-migration hook is locally verified; video collection validators
remain a follow-up. Publication and human approval remain pending for all outputs.

See [runtime instructions](../services/api/app/modules/videos/README.md) for exact
live commands and exported integration seams.
