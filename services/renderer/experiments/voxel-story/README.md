# Original 3D voxel story

See [the reusable template guide](../../templates/voxel_story/README.md) for the
reference breakdown, model-building approach, story grammar, run commands and
integration limits. `storyboard.json` is the new common-pool resource lesson.

Generated outputs stay in `.local/voxel-story/output/commons-lake/` at repository
root. `lesson.mp4` is the video; `contact.jpg` contains encoded inspection frames;
`technical-report.json` records checks; `CREDITS.txt` carries source attribution.

This is a local authored template and sample. New topics reuse the stage, rig,
caption/voice pipeline and story grammar, with new props/actions implemented and
reviewed explicitly. It is not wired into the production feed.

## Cinematic direction revision — implementation only

`src/ShotDirection.ts` adds authored multi-key camera plans, smootherstep moves,
explicit cuts, focal-length changes, and cues resolved from existing aligned
words. Catch and release shots follow the existing physical event timeline.
`src/Acting.ts` adds an opt-in face rig, expression poses, staggered surprise,
and a neighbor noticing the lead's catch. Both use absolute time so rendering
a frame does not depend on having rendered the previous frame.

The lake adapter uses warmer key light, cool ambient shadows, gradual color
changes with matching fog, and lower caption placement to reserve the central
action area. Other ModelKit consumers keep their existing rigs. No packages,
provider calls, new narration, or public contract fields were added.

Direction revision: `voxel-cinematic-v3`. Existing staged narration can be reused
with the updated source; no preparation/provider call is needed for a visual-only
render. Existing MP4s and their earlier technical reports still describe the old
render. **This revision has not been tested, rendered, previewed, or creatively
approved: the user explicitly deferred testing.** Before promoting a future
render, inspect every shot's start/action/end, camera cuts, faces, hand/prop contact,
caption clearance, and the complete encoded movie.

Design reference: [claude-animated-shorts skill](https://github.com/mromidev/claude-animated-shorts/blob/main/SKILL.md)
and its [shot implementation](https://github.com/mromidev/claude-animated-shorts/blob/main/templates/bridge/story.ts).
The new code is original; no upstream footage, characters, scripts, or reference
frames are included. This adapts shot/acting techniques, not their full postprocessing
pipeline or no-caption policy.
