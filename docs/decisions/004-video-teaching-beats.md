# 004 — Measured teaching beats and concept-only default

Owner: Agastya. November 14, 2026.
Status: implemented locally under the user's research-driven tuning request;
effectiveness remains an experiment.

## Decision

Add optional `teaching_beats` to the internal Storyboard schema and require the
five-beat structure for new generation. Measure opening timing after narration,
insert real thinking pauses, and repair timing within the existing bounded workflow.

Default new renders to `VIDEO_BACKGROUND_MODE=concept_only`. Explicit `gameplay`
preserves the earlier presentation for comparison. This deliberately revises
PROJECT.md's original Minecraft-background default under the user's current request.
See [the evidence and its limitations](../VIDEO_ENGAGEMENT_RESEARCH.md).

## Interfaces and migration

- No public API, LessonRequest, format ID, ownership or quiz fields are renamed.
- Storyboard's additive field contains `{kind, segment_id, text}`. Historical
  artifacts without it remain readable; new generation requires all five beats.
- Internal timed lessons add `{kind, text, start, speech_end, end}` beats and
  `background_mode`. Times are seconds relative to the audio track.
- The renderer hides answer-bearing visuals during questions and preserves captions.
- Generation identity includes policy version, system prompt hash and background
  mode. Rebuild the renderer image before generating with updated code. Existing
  ready assets stay intact; no database migration or new service is introduced.

## Alternatives and integration

Prompt-only guidance cannot guarantee real silence or prevent a visible diagram
from revealing an answer. Removing dialogue would discard the requested character
interaction. A learned ranker needs behavioral/learning data and an experiment.

Amogh supplies the same approved brief; Adi consumes the same MP4 and captions.
The spoken self-check does not create a client quiz or graded attempt.
