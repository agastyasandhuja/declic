# Voxel causal story — template v2

User requested all three qualities of the supplied reference: a 3D Minecraft-like
world, causal storytelling and short white captions. This is a runnable local
authoring template and example, pending creative approval; it is not a new public
format ID or an automatically integrated production generator.

## What the reference actually does

Inspected the user-supplied `v292ffg50001dbpsccnog65k19d88fdg.MP4` locally: 576×1024,
30 fps, 73.514 seconds including its platform outro. Sampled frames every three
seconds and read the captions with on-device Apple Vision at eight frames/second.
OCR is imperfect; it is observational evidence, not a verbatim certified transcript.
No reference footage, textures, voices or audio were incorporated into the sample.

| Approximate time | Story job | Visible device |
| --- | --- | --- |
| 0–6s | Topic, then contradiction: best month but falling price | Price board, crowd, emeralds, shop |
| 6–15s | Establish owner, business, expansion constraint | Named shopkeeper, goods, shop divided into ownership pieces |
| 15–26s | Give the abstraction a tangible object | Buyer holds a share; currency and profit make ownership concrete |
| 26–37s | Expand the world and raise expectations | Trading crowd, second shop, imagined expansion |
| 37–46s | Explain the mechanism and raise the stakes | Prices track expected future earnings; buyer buys again |
| 46–55s | Pay off the contradiction | Good performance misses expectations; sellers gather and price falls |
| 55–69s | Transfer analogy to a real example; return to the buyer | Office cutaway, then the original shop and buyer |
| 69–73.5s | Platform outro | Not a teaching beat; omitted from our template |

The visual appeal appears to come from a persistent, navigable world, recognizable
characters, physical transfers of props, and close/medium/wide cuts. The camera
often pushes or drifts while a meaningful action happens. Crowds and particles
support the event. These are creative observations, not measured engagement claims.

Captions are mostly **one word at a time**, bold white sans serif, dark edge/shadow,
roughly centered vertically. They transcribe speech rather than add paragraphs.
Persistent labels are limited to useful in-world information such as prices/names.
Our version uses the same short white treatment with a small entrance pop, avoids
names/branding, and keeps the full world visible.

The reference's explanation of profit payments is an analogy, not a universal
statement that all stocks automatically pay weekly dividends. Future lessons must
review the underlying claims independently rather than copying reference claims.

## Reusable story grammar

1. **Contradiction:** show a surprising outcome before explaining it.
2. **Ordinary goal:** one person wants something concrete.
3. **Physical model:** turn the concept into a prop, place, transfer or constraint.
4. **Causal escalation:** other people respond; every shot changes the world.
5. **Reversal:** the intuitive action produces an unexpected result.
6. **Mechanism:** name the concept after the audience has seen it happen.
7. **Resolution/transfer:** demonstrate a changed rule or condition and return to
   the opening. Include limitations without turning the ending into a lecture.

Target 105–145 words and 35–55 seconds. Budget 2–5 seconds per shot, with longer
holds only when required by a visible action. Use a varied stock narrator rather
than cloning the reference voice. Freeze speech before aligning captions/cues.

## Models and animation

The executable example lives in `../../experiments/voxel-story`:

- `src/ModelKit.ts` and `src/World.ts`: genuine Three.js geometry, perspective camera, lighting, shadows,
  original nearest-filter pixel textures, articulated humanoid factory, fish factory,
  crates, houses, trees, dock, rods and water. Characters have separate head, arm
  and leg pivots. Props use stable world coordinates, so camera moves produce parallax.
- `src/Root.tsx`: frame-driven animation, aligned narration, one-word white captions.
- `../../src/PopCaptions.tsx` relative to this guide is the shared caption source;
  the runner mounts it read-only into the isolated render. Keep this dependency
  when copying the template into another checkout.
- `storyboard.json`: frozen script, camera endpoints/targets and scene selection.
- `models.py` and `lake-story.schema.json`: closed, bounded authoring schema for
  the implemented lake adapter; validate before incurring narration calls.
- `prepare.py`: uses existing server-side ElevenLabs synthesis/alignment and cache.
- `run.py` / `render.mjs`: local assets only, pinned Three.js, existing isolated
  Remotion Docker runtime, CPU/memory/time limits, no network or app credentials.
- `sound.py`: original quiet water/splash sounds. No copied soundtrack.

For another topic, retain the rig, stage, camera/caption/narration pipeline and
story grammar. Author the topic's props and action adapter: e.g. mine → ore → furnace
for a bottleneck, forest → logging → regrowth for a common resource, or workshop →
specialized tasks for comparative advantage. Changing narration alone does **not**
create a good new lesson. The supplied action adapter implements the lake story;
new mechanisms require authored geometry/motion and visual review.
The lake adapter's ID and eleven action phases are intentionally fixed in its
schema; a new adapter must define its own supported actions rather than bypass
validation or pretend that arbitrary scene names are implemented.

No Blender install is required for these block models. More detailed future rigs
could be authored in Blender/Blockbench and exported to glTF, but that pipeline
has not been implemented or validated here. Procedural source is the editable
model deliverable for this version; there is no claimed `.blend` or `.glb` export.

## Example: tragedy of the commons

The new video opens with the village fishing itself out of dinner, rewinds to
open access, shows individual overharvesting becoming collective depletion,
then demonstrates rules and monitoring. Recovery occurs over compressed time;
the fish are illustrative, not a calibrated ecological simulation. It deliberately
avoids claiming common ownership inevitably fails or that any arbitrary quota
guarantees recovery.

Factual basis: [FAO on common-property fisheries, rules and monitoring](https://www.fao.org/4/a0312e/a0312e03.htm)
and [2009 Nobel economics announcement on Ostrom's empirical findings](https://www.nobelprize.org/uploads/2018/06/press-7.pdf).
Renderer reference: [Three.js WebGLRenderer documentation](https://threejs.org/docs/pages/WebGLRenderer).

## Reproduce and review

From repository root, with the existing API venv, ffmpeg and renderer image:

```sh
python3 services/renderer/experiments/voxel-story/fetch_vendor.py
PYTHONPATH=services/api services/api/.venv/bin/python services/renderer/experiments/voxel-story/prepare.py
python3 services/renderer/experiments/voxel-story/sound.py
python3 services/renderer/experiments/voxel-story/run.py stills
# Inspect the actual frames before the full render.
python3 services/renderer/experiments/voxel-story/run.py video
python3 services/renderer/experiments/voxel-story/finalize.py
python3 services/renderer/experiments/voxel-story/verify.py
```

Generated media, reference analysis, provider cache and downloaded dependency stay
under ignored `.local/voxel-story`. Server credentials are read only by narration
preparation, never passed to the renderer. No reference upload is needed.

Review motion as well as stills: articulated limbs, object handoffs, resource
depletion, rule checking, release/recovery, framing, caption legibility and audio.
An MP4 header or successful render alone cannot approve the format. Physical-iPhone
playback, hosted storage, production catalog and measured learning gains require
separate validation.


### Sample 22 motion revision

The user endorsed captions but rejected actors facing away from their task.
Revision 2 uses target-derived facing, hand-attached rods, articulated elbows,
phased casting/reeling/depositing, individual blinks/reactions, dry-bank crowd
paths and lake-side cameras. `Blocking.mjs` owns deterministic action scheduling;
its geometry tests check facing, paths, shortest turns and unique fish transfers.
`ModelKit.ts` holds Codex-authored reusable assets. No additional Claude, Astra
or ElevenLabs calls are needed for this revision; existing narration is reused.
Follow `../../ANIMATION_STANDARD.md` for all future animated formats.

### New-topic template trial

`../../experiments/election-story` tests the same rig and captions on U.S.
presidential elections with new civic props, ballot handling, state vote transfers
and supporting 2D diagrams. It has its own bounded action schema; the lake's scene
enum was not widened to claim support for arbitrary topics. See that adapter's
README for factual sources, shot plan and reproducible commands. The simultaneous
`../../experiments/spin-story` trial applies the shared captions and review standard
to a new 2D cartoon on angular momentum. These are authored local examples pending
user review, not production format promotion.
