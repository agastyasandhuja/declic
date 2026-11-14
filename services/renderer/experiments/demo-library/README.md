# Locally authored generic demo library

Operator-only author/import path, with no Claude API call. Local Claude Code or
Codex can supply bounded JSON; a rendered file is still **pending content, visual,
continuous motion/audio and generic-lineage review**. These are procedural teaching
scenes, not retrieved footage or evidence of educational effectiveness.

Six presentations share exact scene data: dialogue character assets, graphics,
worked mathematics, cartoons with task-facing arm rigs, real Three.js geometry,
and timelines. Geometry reuses the retained ModelKit. Every narrated presentation
uses white single-word PopCaptions. `matrix_a` / `matrix_b` mean multiplication:
code computes each dot product. For RREF/rank/eigenvectors use explicit nodes and
row-operation equations, not that multiplication input. Authors must verify all
other quantities and historical claims. No arbitrary scene code, remote assets,
private course documents or credentials are accepted in lesson inputs.

From `services/api`, using the API venv:

```sh
python -m app.modules.videos.local_demo schema --output /tmp/demo-schema.json
python -m app.modules.videos.local_demo validate --input /path/batch.json --output /path/validated.json
python -m app.modules.videos.local_demo prepare --input /path/validated.json --output /path/work --assets-root /path/repo --env-file /path/repo/.env --workers 2
```

Preparation uses configured ElevenLabs voices and content-addressed speech cache.
`--narrator-voice ID` selects a deliberately cast voice; `--only ID,ID` limits a
retry to named lessons. `--local-speech` explicitly uses macOS speech with estimated
alignment, recorded in the pack. It never silently changes provider on failure.
Measured duration must be 30–60 seconds and the opening at most six seconds.
Failed duration checks preserve cached audio and a private timing diagnostic.

From the repository root, with `PYTHONPATH=services/api`:

```sh
python services/renderer/experiments/demo-library/run.py stills --id demo_example --work /path/work --vendor /path/repo/.local/voxel-story/vendor/three.module.js
python services/renderer/experiments/demo-library/run.py video --id demo_example --work /path/work --vendor /path/repo/.local/voxel-story/vendor/three.module.js
```

The existing v10 renderer image supplies cached dependencies. It runs non-root,
network-disabled, read-only except bounded temporary/output mounts, with no
application credentials and explicit CPU/memory/PID/file-size/time limits. Run at
most two simultaneous renderer processes on the demo Mac. Three.js bytes are
pinned by hash. Outputs retain lesson/pack/source provenance. Stills cover the
start, midpoint and end of each spoken scene; inspect these and the full motion
and audio before writing an explicit final review. The video path runs existing
media validation and rejects files above 45 MiB. It neither publishes nor marks
any review passed. Shared publication is a separate reviewed operator action.

Scene limitations: nodes and their interpolated endpoints are schematic; a graph
edge is a relationship, not necessarily a physical rope. Cartoons use authored
actors and props rather than an arbitrary action generator. 3D figures face their
nearby task; scenes that require lifting, tool use or realistic contact need
specific geometry/motion work and inspection. Parent-authored scene data still
requires factual and visual review for each new topic.
