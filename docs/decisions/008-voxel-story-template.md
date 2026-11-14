# 008 — Local voxel story template

Status: experimental implementation, November 14, 2026; production integration proposed.

The user supplied a 3D Minecraft-style stock-market video and requested a reusable
template plus an original video on another topic, confirming that the models,
camera work, storytelling and captions all matter.

Use original procedural cube models in Three.js within the existing Remotion
renderer. This adds a local experimental dependency, Three.js 0.170.0, fetched to
ignored storage with pinned SHA-256 and its MIT license. It does not introduce a
service, modify Adi's JS lockfile, change any public contract fields or publish a
new format enum. No Minecraft game asset extraction or reference re-use is needed.

The authoring template is `services/renderer/templates/voxel_story`; its first
executable adapter is `services/renderer/experiments/voxel-story`. The example
explains common-pool resource incentives and collective rules with a fishing lake.
The isolated renderer receives staged original script-derived assets only.

Production adoption would require Adi to integrate the pinned dependency through
the canonical JS manifest/lockfile, Agastya to integrate validated scene data and
renderer packaging, and a reviewed template/version selection within the existing
`analogy_story` format. Continue using ordinary MP4 + captions delivery. Topic
changes require factual review and an action adapter; there is no generic automatic
3D world generator or claim of app/iPhone integration in this experiment.


November 14 follow-up: the user approved caption style but requested stronger
animation throughout, especially task-facing bodies. The kit is now extracted
into `ModelKit.ts`, with deterministic blocking/actions in `Blocking.mjs` and
regression checks for facing, shore paths and fish identity. Codex owns reusable
asset/action authoring by default; GPT-6 Astra API is an optional approved tool
for harder assets, subject to actual configuration. This does not claim an Astra
integration exists. This revision made zero additional paid generation calls.

The white single-word treatment is shared through `src/PopCaptions.tsx` across
narrated renderers. Existing outputs are not silently claimed to have changed;
samples 22 and 21 are explicitly rerendered. Main renderer template recipe is
4.1.0 and the verified local image is `hackumass-renderer:reference-v8-captions`.
Shared caption source participates in recipe hashing. No wire fields changed.
