# Animation craft and reusable assets

User direction, November 14, 2026, after sample 22: keep the white single-word
caption treatment; put substantially more care into every animation; make people
face their task instead of posing for the camera. This applies to all new and
revised animated formats, not only the lake example.

## Author once, reuse deliberately

Codex authors, reviews and repairs reusable models, rigs, props, action code and
camera staging directly in this repository by default. Inspect the existing
asset catalog before making new geometry. Save useful work as reusable functions,
with a version and demonstrated actions. Reuse cached voice/alignment when the
script is unchanged. Do not call Claude just to redraw an existing prop, recolor
a rig, change its pose or repair renderer code.

GPT-6 Astra API is also user-authorized as an option for harder new model work.
Check the configured provider and actual supported model name before using it;
do not invent an endpoint or claim an API is connected. Claude remains an option
for genuinely useful planning/review tasks. This policy does not remove factual
review or silently change the existing production model routing. Record actual
calls and cache reuse; estimated savings are not measured savings.

Reusable inventory:

| Asset/action | Owning source | Reuse boundary |
| --- | --- | --- |
| Block humanoid with head, shoulders, elbows, hands, legs and eyelids | `experiments/voxel-story/src/ModelKit.ts` | Parameterized shirt/skin/hair; +Z is forward; hands expose world transforms |
| Fish, crates, cube geometry, pixel textures and beams | same model kit | Original procedural geometry; no game extraction |
| Facing, shortest-angle turn, phased fishing poses and shore paths | `experiments/voxel-story/src/Blocking.mjs` | Generic facing/turn helpers; lake paths and events remain scene-specific |
| White word captions | `src/PopCaptions.tsx` | Provider timing; responsive size; safe placement can vary by format |
| Camera key sampling, word cue lookup and lake shot plans | `experiments/voxel-story/src/ShotDirection.ts` | Generic sampling/cues; authored lake coordinates are scene-specific. Added November 14, tests/renders deferred by user. |
| Opt-in eyebrows/mouth expression rig and timed reactions | `experiments/voxel-story/src/Acting.ts` | Uses ModelKit head coordinates; reaction selection is lake-specific. Added November 14, tests/renders deferred by user. |
| Connected 2D arm rig, swivel chair and integrated angular motion | `experiments/spin-story/src/Root.tsx`, `Motion.mjs` | Fixed limb lengths, continuous angle, illustrative axial inertia; review new poses before reuse |
| Civic plaza, ballot and distinct electoral-token transfers | `experiments/election-story/src/World.ts`, `ElectionMath.mjs` | Reuses ModelKit; election state/rules remain topic-specific |
| Existing physics/biology/payment scene adapters | `src/DecisionScenes.tsx`, `BiologyScenes.tsx`, `PaymentScenes.tsx` and experiments | Reuse mechanisms only when the new facts fit; inspect each new shot |

## Each shot needs acting, blocking and a visible result

Before rendering, specify actor/prop start state, target, anticipation, contact,
action, follow-through and settled end state. Connect cue timing to speech.

- **Facing and eyelines:** derive body direction from the task/interaction target.
  Turn the head toward a relevant object or partner. Position the camera to see
  that action; do not rotate everyone away from their task to show faces.
- **Contact:** parent held props to hand transforms, or solve a grip explicitly.
  A line must meet its hook. Objects travel from source to destination. A caught
  object should not both remain at its source and arrive in the inventory.
- **Support and paths:** feet meet the ground, bodies avoid unintended penetration,
  and walks take navigable paths. Check the entire path, not only endpoints.
- **Acting:** readable preparation and follow-through; weight shift, elbow bend,
  differentiated reactions, gaze and occasional blinking. Stagger a crowd's
  actions. Avoid perpetual synchronized swaying/waving as a substitute for acting.
- **Continuity:** preserve object identity, count and ownership through transfers.
  Make compressed time or a deliberate reset understandable. Do not hide a causal
  discontinuity with a camera cut.
- **Camera:** compose wide/medium/close shots for the mechanism. Keep hand contact
  and the payoff visible; avoid poles across faces, foreground occlusion, accidental
  clipping and important geometry under captions. Motion should have a reason.
- **Polish:** use easing appropriate to mass/contact, secondary motion after primary
  action, and quiet synchronized foley. More particles do not fix unclear staging.

## Inspect before declaring completion

Inspect beginning, contact/action peak and end of **every authored shot**, plus
transitions and a continuous video pass. Use geometric invariants when possible
(forward vector toward target, held-prop contact, valid paths, transfer counts),
but distinguish these from visual/creative approval. Exported motion-review clips
are inspection aids, not automated proof of professional animation.

Narrated formats use the sample-22 caption component: one currently spoken word,
white bold text, thin dark edge/shadow, quick restrained pop, no color cycling or
stale word held into silence. Choose placement around the scene. Music-led math
keeps its equations and does not invent spoken captions.

Existing exported MP4s retain their old visuals until deliberately rerendered.
Record which samples were rerendered, inspected and approved by the user. Never
claim a policy update improved every historical film automatically.
