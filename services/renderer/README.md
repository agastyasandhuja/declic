# Isolated Remotion renderer

Build from repository root: `docker build -t hackumass-renderer:0.1 services/renderer`.
Use the video CLI documented in `services/api/app/modules/videos/README.md` to run
the broker. Do not execute generated scene modules on the host.

The broker mounts only a staged pack read-only, disables external networking,
drops all capabilities, uses non-root UID 1000, read-only root, bounded tmpfs,
2 CPUs, 4 GB RAM and 256 processes. It never passes application/provider secrets
or a Docker socket. Output extraction permits bounded ordinary files only.
Docker Desktop must be running. The container's loopback HTTP server serves only
staged assets to Chromium; it has no external network access.

`src/Root.tsx` owns portrait safe areas, captions, narration and character layout.
`src/CustomScene.tsx` is the optional Claude-generated phase-animation slot, clipped
to y=300..390. Pointer geometry and code stay in the trusted root after live model
outputs demonstrated incorrect null links. The two
template directories contain teaching prompts; visual-explainer also declares
the allowed scene API. Static source checks are defense in depth; the container
is the execution boundary.

The renderer emits MP4, representative frames and render-result JSON. The trusted
Python broker checks dimensions, codecs and duration, and normalizes full-range
H.264 when necessary. These checks do not replace content, synchronization,
copyright/provenance or device review.

```sh
cd services/renderer
npm ci --ignore-scripts
npm test
npm audit --omit=dev
```

`tests/isolation-probe.mjs` is an operational probe to run under the same Docker
constraints; it checks UID, mounts, credentials, network, PID/memory caps and
capability restrictions. Never weaken the broker to run model-generated code.
