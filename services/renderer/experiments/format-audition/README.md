# Educational format audition

Nineteen local concept samples derived from the two research briefs supplied on
November 14, 2026. These are **candidate formats awaiting the user's selection**,
not production feed formats or evidence of retention/learning improvements.

Each sample has an original synthetic script, a distinct teaching mechanism,
live ElevenLabs narration and character-level alignment, authored SVG/Remotion
scenes, a candidate manifest, frame exports and an MP4. Several formats intentionally
share a topic for comparison. The sample IDs are internal to this experiment;
the public `VideoVariant.format_id` enum is unchanged.

These are 2D/2.5D auditions. Curiosity is a wave diagram, map is a fictional weighted
graph, technology is a gravity-storage schematic, history is a causal algorithm
reconstruction, and POV is an illustrated fictional market. They do **not** validate
Three.js, MapLibre, historical accuracy, generative video, real footage, or a
fully parameterized general-topic template. Dialogue uses one narrator, not a
validated two-voice performance. Keepers need subsequent art direction and
parameterization based on user feedback. See each manifest's limitations.

## Reproduce

From the repository root, using existing dependencies and the existing isolated
renderer image `hackumass-renderer:reference-v7`:

```sh
PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/format-audition/prepare.py
python3 services/renderer/experiments/format-audition/run.py stills
python3 services/renderer/experiments/format-audition/gallery.py
PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/format-audition/review.py
python3 services/renderer/experiments/format-audition/run.py video
python3 services/renderer/experiments/format-audition/finalize.py
python3 services/renderer/experiments/format-audition/verify.py
python3 services/renderer/experiments/format-audition/gallery.py
```

`prepare.py` reads ignored server env files, uses the configured narrator/model,
and reuses the existing content-addressed speech cache. It makes live provider
requests for cache misses. `review.py` invokes the configured video Opus model
on real contact sheets and caches exact inputs. Its findings are advisory: review
their evidence and preserve intentional format choices. It does not listen to
audio or view continuous motion. Never convert an initial critique into a claim
that a changed final video passed without reviewing the changed artifact.

`gallery.py` needs Pillow (available in the machine's `python3`, not the API venv).
`verify.py` requires FFmpeg/FFprobe. No packages or root lockfiles were changed.
`finalize.py` converts Remotion's full-range H.264 to limited-range `yuv420p`
where needed and levels narration toward −16 LUFS. It reuses matching finalized
outputs by SHA-256. `verify.py` similarly reuses reports for unchanged MP4s.
`run.py video --only map,character` renders a subset. It has a one-hour process
deadline and runs with no network, no provider credentials, non-root UID, read-only
root and input, dropped capabilities, and CPU/memory/PID/file-size limits.
Only the dedicated local output directory is writable. The base image remains
unchanged; the experiment is mounted separately and webpack runs inside Docker.

Outputs are ignored under `.local/format-audition/`: `index.html`, `registry.json`,
per-sample `pack/` scripts/audio/VTT, `output/` frames/contact sheets/MP4s, provider
caches, critique reports and technical reports bound to final MP4 hashes. Do not
commit or publish these files automatically.

## Feedback and skills

Open the gallery to play samples. Keep/Potential/Pass and notes save in the browser;
**Export feedback** downloads a JSON copy. Opening the page does not mark anything
approved. Browser choices do not modify repository manifests automatically.
The user can instead give the numbered choices in chat.

Ten concise local candidate skills live in `skills/`. They are saved for this
experiment, not globally installed. `skill-sources.json` records the specific
upstream revisions consulted and the guidance actually applied. We did not install
or execute third-party skill scripts. The wider list of suggested Manim, map,
B-roll, WebGL and other skill packs has not been benchmarked by this run.

Sampled stills, exact arithmetic, executed Python examples, caption timestamp
bounds, full video decode, encoding and non-silent audio checks have different
purposes. None establish natural voice delivery, iPhone playback or educational
effectiveness. Production spoken lessons still have the 30–60-second contract;
shorter clips here are format auditions only.

The later friction story revisions are samples 20 and 21, reproduced from their
sibling experiment folders. Sample 21 is the user-endorsed direction for relatable
physical stories; remaining animation polish is still under review. The new
`real-world-humor` skill uses the executable story planner, scoped novelty history
and shared pop captions. This does not imply arbitrary scene generation is solved.
