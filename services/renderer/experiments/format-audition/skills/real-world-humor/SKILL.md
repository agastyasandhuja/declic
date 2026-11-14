---
name: real-world-humor
description: Build distinct, grounded, lightly funny everyday stories for physical college concepts.
---

# Real-world humor and stories

Read ../../../CREATIVE_DIRECTION.md and the current lesson's approved facts.
The user liked the revised friction sequence: familiar consequences, a small
physical joke, then a visual causal explanation. Retain that structure while
varying the actual story. Do not recycle the mom/dog/phone/gym sequence by
changing names.

For model-assisted planning when useful, the optional executable planner is at
`services/api/app/modules/videos/generation/story_engine.py`, through
`python -m app.modules.videos.story_cli`. It tries three alternatives, validates
structure and fact references, compares recent setups/punchlines, then audits
physics and the relationship between joke and visible action. Histories must
remain owner/catalog scoped. See the videos module README for exact invocation.
Rejected plans receive up to two targeted repairs, with a new audit after each,
before moving to another alternative. Keep actual comic expectations/reversals in history;
reusing an underlying physics principle is not itself repeating a joke.

Build each joke from an ordinary goal, an expected outcome and a visible
reversal. A short dry reaction can land after the physical result; a confident
line can precede an immediate failure. Use one or two gags, not banter on every
line. Do not treat a formula rewritten as a punchline as successful humor.
Rotate overconfidence, understatement, literal consequences, reversal and
scale mismatch. Avoid generic meme filler and repeated catchphrases.

Default to college-level concepts and male voices. Use the planner's selected
narrator ID when synthesizing the next authored story.
It rotates Liam, Roger, Charlie and Callum across recent scoped plans and avoids
the last two leads. Treat that as planned casting until synthesis succeeds;
do not silently replace every selection with the same default narrator.
Keep the explanation precise: a joke cannot invent a physical property or excuse
misleading motion. Only
captions and necessary diagram notation appear on screen. Reuse
`services/renderer/src/PopCaptions.tsx` for the approved white single-word pop.
Codex may author and review plans directly; reuse models and narration instead of
calling a paid model for routine asset or animation repair. Follow the renderer
animation standard and inspect task-facing bodies, contact and camera staging.

The planner produces an internal authoring artifact, not arbitrary finished
animations. Implement the required actions in the isolated renderer, inspect
initial/action/end poses, and verify the encoded result. Keep user creative
feedback separate from model audits and technical checks. Recent draft history
reduces repetition; it does not prove every future story is semantically unique
or funny. Record rejected setups and the user's specific reasons for revision.
