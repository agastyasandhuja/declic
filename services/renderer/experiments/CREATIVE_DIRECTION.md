# Current video audition direction

User direction, November 14, 2026:


Latest user correction after sample 22 supersedes earlier caption/model guidance:
- Use the approved white, single-word, speech-aligned captions with the restrained
  pop from `src/PopCaptions.tsx` across narrated formats. Position around the action.
- Put more effort into every animation: task-facing bodies and eyelines, attached
  props, navigable paths, anticipation/contact/follow-through, varied crowd acting,
  and cameras that reveal the interaction. Follow `../ANIMATION_STANDARD.md`.
- Codex authors and improves reusable models/rigs/actions directly by default to
  avoid unnecessary Claude calls. Reuse existing assets and cached narration.
  GPT-6 Astra API is also permitted for harder model work after checking actual
  availability/configuration. No paid model is mandatory for asset repair.
- The lake's initial camera-facing fishers were explicitly rejected. Its white
  captions were endorsed. Keep those judgments separate; caption approval did not
  approve the first animation. Improve the current sample and future animation work.

Earlier feedback retained below for context:

Follow-up after sample 21: the user said this is getting good and is the right
direction, while some animation quality still needs work. Retain this story
family as a promising format for physical concepts with real-world examples.
Build humor into causal situations, vary setups and punchlines between stories,
and make each new caption phrase visibly pop. Keep the minimal-text constraint.
The first reusable story/humor planner is
`services/api/app/modules/videos/generation/story_engine.py`; it produces
grounded, novelty-checked plans, not automatic new scene animations.

- Prioritize male voices, while still varying voices across videos. A clear male narrator may carry most of a story; extra actors should earn their place.
- Keep stories straightforward: one counterfactual question, several immediately recognizable consequences, an occasional small joke, then a visual explanation of why. Avoid unnecessary fictional lore, named mascots, or forced banter.
- On-screen text is limited to speech captions and essential numbers/letters in diagrams. No episode branding, scene headings, status badges, character names, slogans, decorative footers or redundant explanatory prose.
- Improve the animation by visibly showing the event: wheels lock while a car continues straight, feet lose purchase, bodies lose balance, objects slip from fingers. Camera moves and caption changes do not substitute for those actions.
- Sample 20 was judged close but not good enough: animation and story need revision. It is not an approved template. The next friction audition follows the user's everyday-example structure.

- Use a variety of voices. The same narrator across every video is annoyingly repetitive.
- For suitable topics, use concrete example stories and animated characters: a counterfactual, consequences, then the causal explanation. Character choices may include topical public figures, fictional characters, brainrot characters or an original host. Use Codex with current evidence to consider relevance; label uncertainty about live trends.
- Default future sample topics to college level, not basic multiplication or elementary arithmetic. Examples: angular momentum and torque, eigenvectors and stability, enzyme kinetics and competitive inhibition, conditional probability and base-rate effects, opportunity cost and marginal analysis. Follow course-derived objectives when supplied.
- The friction cartoon is the currently requested storytelling proof of concept. Its university-mechanics extension is static traction, centripetal force and the quadratic dependence on speed.
- Keep the existing format auditions and candidate skills available for user review. A completed render is not an approved reusable template, a demonstrated learning gain or evidence of virality.

This file guides experimental authoring. It does not claim a production voice-rotation scheduler, automatic college-topic selection, or phone integration has been implemented.
