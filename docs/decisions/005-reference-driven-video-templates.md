# 005 — Reference-driven scenes and model-selected imagery

Owner: Agastya. November 14, 2026. Status: implemented locally; media verification recorded in Agastya status.

The user's three video examples supersede the prior static question-card presentation
and concept-only default for the character format. Their requested goal is materially
closer visual output, image retrieval in Claude's workflow, and a third space-style
complex animation template.

## Observed references

Local source files are kept outside Git. Analysis artifacts live under ignored
`.local/reference-analysis`. The three recent Downloads videos match all described
formats: `v12300gd0001dagtaevog65lbfi50iq0.MP4` (121.67s, image-driven explainer),
`ScreenRecording_11-14-2026 01-38-26_1.MP4` (81.35s, space sequence including phone
chrome), and `ssstik.io_1794638670883.mp4` (67.59s, Peter/Stewie AVL explanation).
Sampled frames establish composition; local Whisper transcripts establish the
spoken structure and approximate cadence. They are imperfect transcripts, not source
facts to reproduce.

- Dialogue: continuous full-frame parkour, brief top captions with active-word color,
  large changing topic diagrams/images, mostly one speaker cutout at bottom left.
  No persistent brand header, dashboard panels, speaker name tags, or quiz cards.
- Explainer: full-frame relevant photographs/illustrations, alternating evidence
  layouts and close views, short central captions, camera pans/zooms and cuts.
- Space: multi-plane star/galaxy depth, continuous camera travel, luminous filaments,
  alternating wide and close scale, small centered lower captions, no boxed UI.

## Implementation direction and interfaces

Keep the same API/worker/narration/Remotion stack. Add internal shot/asset planning
schemas. Claude chooses image search queries and returned candidate IDs; the backend
performs bounded retrieval, validates and normalizes image bytes, records attribution,
and stages local files. Renderer network isolation remains intact. Remote metadata
is untrusted reference data, never instructions or factual proof.

Add `space_explainer` to learning format IDs and the integrator-owned feed candidate
model; regenerate schemas. Amogh's academic request shape remains unchanged (existing
suggested_formats is a string array), and Adi consumes ordinary MP4/captions. Record
new format availability in the status handoff; do not silently edit their implementations.

General storyboards must not require a linked-list trace. Retain the validated trace
for linked-list lessons while allowing scene-driven general lessons with approved
fact coverage. New reference presentation uses continuous pacing; the earlier five-beat
policy remains readable for historical artifacts and can be selected deliberately.

New material is not automatically public or ready. Existing ownership, source-grounding,
content review and publication gates remain. No reference creator's audio, watermark or
footage is republished. No character-voice cloning is inferred from these examples.

## Completion evidence required

Three rendered, inspected comparisons; successful live model-driven image selection
and retrieval; image failure/security tests; scene and caption synchronization; no
accidental answer leakage where a quiz is used; broader-than-linked-list generation;
exact artifacts and limitations in docs/status/AGASTYA.md. A passing build alone does
not prove fidelity to the references or engagement gains.

## Implemented retrieval and image composition

NASA and Openverse searches produce bounded candidates. Download allowlist:
`images-assets.nasa.gov`, `upload.wikimedia.org`, `live.staticflickr.com` (HTTPS only,
no redirects). The backend normalizes to local JPEG. Claude visually checks actual
images and plans bounded focal points, wide/close framing and zoom per image shot;
no model-supplied URL or path enters the renderer. Visual or download failures can
select an alternative candidate, within the existing total model budget. Provenance,
license and creator metadata remain attached to the selected image. A synthetic
color-field adapter supports offline fixtures; it is never presented as real imagery.

The reference examples exposed model failures despite passing self-review. Source
claims and final crops need editorial inspection; sample correction records are
kept with their local artifacts. Content-review cache entries now bind to the exact
storyboard digest. Structural validation and media checks are not engagement evidence.

Authored spatial scenes use a bounded four-core/1600-second render profile and a
30-minute pipeline deadline, based on the live local rasterization run. Other
formats retain the previous two-core/1100-second render profile and 20-minute
pipeline deadline. This changes compute allowance, not the renderer's credential,
network, filesystem, memory or process isolation. No new service is introduced.
