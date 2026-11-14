# 001 — API-authenticated generation with isolated rendering

Status: proposed; implementation and provider/device validation pending.

Owner: Agastya. Date: November 13, 2026, America/New_York.

## Problem

Lesson videos need repeatable scripts, measured speech timing, custom animations,
and a bounded repair loop. A single prompt that writes an entire video cannot
reliably synchronize unknown speech duration, and generated code must not execute
with application credentials. Parallel implementation also needs stable artifacts.

## Proposed decision

- Run the Python Claude Agent SDK with an API key inside the existing worker.
- Use approved lesson briefs and versioned script/storyboard/timed-scene artifacts.
- Generate ElevenLabs narration before implementing timed scenes.
- Use structured template data for dialogue/gameplay; allow scoped custom scene
  code for visual explainers.
- Expose only controlled artifact and sandbox-render tools to the agent.
- Compile, discover compositions, preview, and render generated code in an isolated
  environment with no application credentials or external network access.
- Keep jobs, retries, authorization, asset selection, and publication in the
  trusted backend. Add no external queue or new agent hosting service.

## Affected interfaces and ownership

The academic `LessonRequest`, `VideoVariant`, `RenderJob`, feed types, and existing
public routes retain their field names and semantics. Proposed new artifacts are
internal learning schemas owned by Agastya; definitions live in the
[video generation TRD](../TRD_VIDEO_GENERATION.md).

Coordinate a canonical-objective lookup with Amogh if needed to resolve level,
language, and notation without guessing. Coordinate renderer dependencies and
mobile safe areas with Adi. Any new public generation/status route or shared
manifest projection requires an explicit learning-contract update. Private
request/binding identifiers must not leak through shared-video responses.

## Alternatives

- Interactive Claude Code: useful for developing templates, but not the automated
  app generation path selected by the user.
- Headless `claude -p`: viable CLI automation; SDK integration provides structured
  control inside the existing Python worker without a custom subprocess protocol.
- Raw model API with our own tool loop: valid fallback if SDK tool restrictions
  cannot meet the design; more orchestration code to maintain.
- Structured template data only: simplest for dialogue; too restrictive as the
  sole visual-explainer implementation.
- Unrestricted host execution: rejected because template/model output is untrusted.

## Implementation/migration steps

1. Add and validate versioned internal schemas and synthetic fixtures.
2. Prove manually authored boilerplates and sandbox behavior.
3. Implement narration/timing, then Claude generation/repair.
4. Add durable orchestration, scoped reuse, and conditional publication.
5. Validate real providers, actual media, and iPhone playback.

No runtime migration is performed by this decision record. Existing scaffold
contracts remain authoritative until coordinated implementation updates them.
