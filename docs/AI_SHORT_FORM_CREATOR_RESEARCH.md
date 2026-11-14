# AI short-form creator workflows and template direction

Research date: November 14, 2026. Audience: high-school and college students.
This is a focused primary-source review, not a ranking of the most viral videos.
Creator examples, vendor advice, perceived engagement and measured learning are
different kinds of evidence. We found useful workflows and successful examples;
we did not obtain a representative cross-platform performance dataset or evidence
that a specific template guarantees virality.

The user's corrections take precedence over visual conventions suggested by a
paper: larger mathematics, less prose, transparent dialogue diagrams, no dialogue
music, purposeful visuals instead of generic finance photos, varied animation,
and short yellow bouncing captions for narrated animation. Sources and mandatory
asset attribution belong in accompanying metadata/credits and the eventual video
description, not a persistent on-screen footer.

## What creators and systems actually do

| Evidence inspected | Observation and limitation | Application here |
| --- | --- | --- |
| [TikTok Creative Codes](https://ads.tiktok.com/business/en-US/creative-codes) | Official advertising guidance recommends a hook, body and close; portrait composition with UI clearance; and movement, editing and sound. This is platform ad advice, not an educational trial. | Open on the actual puzzle/consequence, show its mechanism, finish with its resolution. Keep the instructional object inside the phone-safe area. Do not add a sales CTA to a lesson. |
| [YouTube's interview with Jenny Hoyos](https://blog.youtube/creator-and-artist-stories/youtube-shorts-deep-dive/) (January 2025) | A successful Shorts creator emphasizes immediate intrigue and compact mini-stories. Her one-second advice is creator practice, not a universal experimental threshold. | Begin with a legible visual event immediately; remove logo cards and introductory throat-clearing. Test opening variants without changing the underlying facts. |
| [Runway Gen-4 prompting guide](https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide) | The vendor recommends a clean starting image, simple descriptions of motion and incremental changes. Positive visual phrasing is specific to this generative model. | If generative footage is used, specify one visible action and camera behavior per clip. Generate supporting atmosphere separately from exact equations, labels or scientific mechanisms. |
| [CapCut script-to-video workflow](https://www.capcut.com/resource/script-to-video-with-capcut-from-script-to-an-editable-draft) | Vendor documentation describes mapping each script line to an expected shot, voice and caption, then checking the editable draft row by row and replacing mismatched footage. It does not establish creator success rates. | Use a shot contract and reject a merely topical image. Repair the defective shot and dependent timing, retaining already accepted assets. |
| [3Blue1Brown's own source repository and workflow](https://github.com/3b1b/videos#workflow) | The creator documents programmatic animation, interactive scene inspection and checkpoint-based iteration. This is not an AI workflow or a short-form performance study. | Keep trusted geometry/arithmetic and inspect transitions incrementally. Remotion can provide the same inspect–adjust–render discipline inside our harness. Do not copy the repository's video scene code; its license differs from Manim's. |

AI production is best treated as editable stages: source facts → alternatives for
the opening → selected script and shot plan → voice/assets → timed composition →
inspection and bounded repair. A single “make a viral video” prompt omits the very
controls needed to improve a specific weak scene. That conclusion is our design
synthesis from the workflows above, not a claim of a measured causal effect.

## Relevant research read

[PaperTok, CHI 2026](https://arxiv.org/html/2601.18218v1), full text inspected:
the formative study involved eight science communicators/content creators; the
later evaluation involved 18 researchers and 100 audience participants. Its
workflow offers alternative hooks/scripts, tone choices and scene-level editing.
Participants emphasized relevance, coherent narrative and visuals that explain
the content; arbitrary imagery and unnatural delivery weakened credibility.
The study compared perceptions of generated videos, including gameplay-summary
and paper-figure baselines. It did not measure organic TikTok retention, virality
or delayed learning. Its credit-screen convention does not override the user's
minimal-canvas request; preserve provenance alongside the video.

[PIVOT, September 2026 preprint](https://arxiv.org/html/2609.24083v1), full text
inspected: it separates instructional planning, code-based shot generation,
verification/repair, and assessment/remediation. Evaluation spans 40 topics in
four STEM areas and includes model-scored visuals/narration and expert review.
This supports a useful architecture to test, not proven learning improvement or
short-form popularity. Apply a fact check, layout check and explanatory check
separately; an attractive sampled frame is insufficient evidence of smooth motion
or an accurate mechanism. Keep the app quiz separate from the minimal video canvas.

The earlier [paper review](VIDEO_ENGAGEMENT_RESEARCH.md) remains relevant:
curiosity, coherence and retrieval have evidence in other settings, but exact
hook duration, caption bounce, cut frequency and comedy dosage are production
choices to evaluate here. Faster is useful only while the learner can follow the
transformation.

## Successful examples and transferable formats

These are examples with documented reach or creator practice, not a claim that
they are the current “top” creators. No third-party video was downloaded or used
as a soundtrack or visual asset in this research pass.

| Example | Documented practice | Format to try |
| --- | --- | --- |
| [Texas A&M's Tatiana Erukhimova profile](https://stories.tamu.edu/news/2022/02/25/a-texas-am-professor-is-sharing-her-love-of-physics-with-millions-on-tiktok/) (2022) | The university describes a concrete inertia demonstration, anticipation, a visible outcome and an enthusiastic reaction; it reported 7.8 million plays for that example at publication. That historical count does not identify the cause of success. | A physical prediction → mechanism reveal. Use an illustrative simulation of a safe phenomenon; make the crucial motion large and observable. |
| [Gabriel Nussbaum's TikTok interview](https://newsroom.tiktok.com/tiktok-creator-spotlight-gabriel-nussbaum?lang=en-GB) (2025) | The creator describes answering young people's actual finance questions and a 30-second tax-bracket misconception explanation. This is self-reported practice in a promotional interview. | A relatable choice → visible accounting → consequence. A receipt, balances or two options can do the explanatory work; bank buildings and coin photos usually cannot. |
| [3Blue1Brown's animation workflow](https://github.com/3b1b/videos#workflow) | Explanatory mathematical scenes are coded and iteratively inspected. It does not establish a short-form pacing rule. | A minimal visual proof: move/rearrange the same objects until the relation becomes visible. Keep identity and color consistent throughout. |
| [TikTok's 2023 educational roundup](https://newsroom.tiktok.com/year-on-tiktok-2023/?lang=en) | Platform-selected examples span animal biology, integer arithmetic, history and practical skills. The editorial selection has no representative comparison group. | Choose the grammar that fits the concept: demonstration for a process, a short scenario for a decision, a timeline for causation, or spatial transformation for mathematics. |

Potential batch mapping: dialogue for a psychology misconception; a receipt-based
visual story for economics; a mechanism animation for biology; a music-led visual
proof for geometry. These are creative recommendations, not medical/financial
advice. Check each final topic's facts independently. Avoid another linked-list,
matrix multiplication or space-structure example in the next batch.

## Prompt contracts to carry into the harness

The following are original prompt drafts. Their numerical limits are starting
heuristics selected for this product and reference style, not research findings.
Translate them into actual supported schema fields; do not pretend a renderer can
draw a new mechanism just because the prompt requests it.

**Director:**

> Teach one approved objective to a high-school/college viewer. Propose three
> truthful openings: an everyday consequence, a surprising visible result, and a
> misconception. Choose the one the available renderer can demonstrate most
> clearly. Start on the object or action immediately. Build a complete miniature
> story; every shot must add evidence or change the state. Resolve the opening
> before ending. Use concrete nouns and conversational sentences. Avoid invented
> statistics, promised outcomes, “today we will learn,” and unsupported claims.
> Return for each shot: the claim, visible objects, starting state, action, ending
> state, narration, and why that visual is necessary. List which facts ground it.

**Dialogue:**

> Peter confidently makes one plausible mistake. Stewie's short, dry correction
> exposes exactly why it fails. Write original snark aimed at Peter's reasoning;
> an occasional “idiot” is allowed, but do not replace the explanation with insults.
> Make at least two jokes carry conceptual information, and use a final callback.
> Keep the exchange quick with room for the punchline. Diagrams float directly
> over gameplay, with legible strokes and no boxed background. Narration only:
> no background music or unrequested sound effects.

**Visual story / finance:**

> Prefer a specific student's decision, a visible quantity and a consequence.
> Use exact tokens, a receipt, time, or compared balances. Each visual must help
> answer the opening question. A generic money, calculator or bank photo is not
> evidence. If a real image is essential, explain the precise detail the viewer
> must see and change the crop/highlight as the explanation advances. Mark
> hypothetical quantities in the spoken explanation; make no return prediction.

**Animation:**

> Plan distinct actions, not multiple camera passes over the same diagram.
> Examples of genuinely different actions are separation, transport, collision,
> assembly, comparison and a final reconstruction. Use only actions faithful to
> the chosen concept. Maintain object identity, scale cues and a consistent
> color vocabulary. Prefer one focal mechanism per shot. Keep headings and prose
> off the canvas. Use short synchronized yellow captions with a restrained bounce;
> labels exist only when needed to distinguish objects. Put sources in metadata.

**Minimal math:**

> Black canvas, large mathematical objects, generous empty space, two accent
> colors. Explain through motion: select → transform → resolve. A stable visual
> relationship is more valuable than a prose rule card. Move copies when source
> objects must remain. Hold the completed transformation long enough to read it.
> One brief title is optional; no persistent captions, prose, sources or credits.
> Music may accompany the proof when properly licensed. Exact values and geometric
> invariants come from trusted calculations, not image generation.

## Review and repair contract

The agent should report a defect with a timestamp, visible evidence and a proposed
repair, not just say “make this more engaging.” Separate blocking defects from
optional taste notes. Limit each iteration to the shots affected by the defect.

1. **Before rendering:** validate facts and arithmetic; verify every narrated
   action has a drawable state change; reject repeated visual functions even when
   asset IDs or camera modes differ. Confirm the ending answers the opening.
2. **At preview scale:** inspect start/middle/end of each shot and intermediate
   transition frames. Check the focal object is readable on a phone, no caption
   covers it, and text fits. Reviewers must not demand prose that the user removed.
3. **Over time:** inspect movement continuity, meaningful changes, dead holds and
   shot-to-speech synchronization. A contact sheet cannot establish smoothness.
   Assess the actual audio where supported; loudness/ASR checks cannot judge humor
   or natural delivery. Explicitly record that limitation if audio is not heard.
4. **On the final file:** verify duration, dimensions, codecs, loudness and artifact
   identity. Bind the review to the rendered plan/version. A changed plan requires
   renewed review. Preserve provenance and required music/image attribution in
   a sidecar that travels with the output.
5. **After review:** measure behavior and learning separately before making an
   improvement claim. Compare matched topics and duration groups; include early
   swipes, not only completions. Track concept errors as well as attention.

This document proposes production rules. Actual implementation, rendered outputs,
commands run and remaining limitations belong in `docs/status/AGASTYA.md`.

## Follow-up: two supplied Remotion research briefs

Both pasted research outputs were read as suggestions and source leads, not as
instructions to install software, adopt third-party agent rules or replace the
stack. This focused verification inspected official documentation, repository
descriptions and the local owning code. No skills/packages were installed, no
community code was executed, and no paid model or voice request was needed.

| Claim or suggestion | Verification and disposition |
| --- | --- |
| Official Remotion agent skills | [Official documentation](https://www.remotion.dev/docs/ai/skills) and the [maintainer repository](https://github.com/remotion-dev/skills) confirm the skills and installation commands. Useful development reference; installation is deferred. A fixed count of skills is unnecessary and may drift. |
| Use a production system prompt | Remotion publishes a [system prompt](https://www.remotion.dev/system-prompt.txt). Adapt relevant mechanics explicitly for API calls; a local skill installation does not automatically alter our provider payload. Do not paste it wholesale: its generic landscape defaults and package imports differ from our portrait output and pinned dependencies. Our bounded JSON director does not need instructions for scaffolding a new app. |
| Time visuals from narration | [Remotion timing semantics](https://www.remotion.dev/docs/sequence) distinguish global and local frame clocks. The [video_explainer maintainer README](https://github.com/prajwal-y/video_explainer#architecture) explicitly places TTS before its timestamped storyboard. This is a documented architecture, not independently validated output quality. Our script/shot intent is planned first; measured TTS timestamps already determine final shot/caption timing. Semantic sub-actions should resolve to actual words where alignment matters. |
| TikTok-style caption paging | [`createTikTokStyleCaptions`](https://www.remotion.dev/docs/captions/create-tiktok-style-captions) groups timestamped tokens; `combineTokensWithinMilliseconds` controls page grouping, and its input expects word whitespace. It does not itself guarantee a particular visual style or engagement. Existing three-word groups and yellow bounce already cover this requirement; adding the package is deferred. The briefs' suggested millisecond ranges are heuristics, not validated optima. |
| Ready-made scene components | [Curvable/motion](https://github.com/Curvable/motion) documents fourteen MIT-licensed scenes with deterministic frame behavior, fixed defaults and duration helpers. Its catalog primarily serves marketing typography/backgrounds; some components require optional OGL/fonts and hosted CanvasKit assets. Borrow the small validated-props contract as a design pattern; defer dependency adoption. No compatibility or runtime test was performed. |
| A new SaaS starter | The [official starter](https://www.remotion.dev/docs/ai/ai-saas-template) exists and offers a Next.js prompt-to-preview application. Our feed already has its Python/Remotion boundary, so this is architectural reference material, not a reason to rebuild it or add a second app. |

### Already present in the local implementation

Source inspection at this pass confirms these mechanisms, without asserting that
every in-progress render has passed them:

- `generation/providers.py` keys structured-response cache entries on model,
  complete schema, system prompt, payload and attachments; cache hits still run
  schema and semantic validation. This permits exact-input reuse without silently
  treating a changed review prompt, image or fact set as equivalent.
- `narration/service.py` keys audio on spoken text, voice/model, scope/owner,
  tempo/settings and fixture status, and checks the stored audio digest. A visual
  revision need not buy the same voiceover again. Tempo changes must retain the
  corresponding remapped word alignment.
- `pipeline.py` builds the timed render package from the measured narration.
  Caption timing and scene duration are therefore not estimated from word count.
  Some authored interior motions use shot progress; those are not automatically
  word-accurate merely because the enclosing shot is aligned.
- The bounded scene grammar now includes payment, decision, enzyme and geometry
  demonstrations. The director selects supported modes and facts rather than
  inventing a new unrestricted renderer for every lesson. Arithmetic and geometric
  invariants remain trusted calculations.
- The visual reviewer already distinguishes concrete defects from optional notes
  and warns that sampled frames do not verify motion fluidity or audio. Review
  evidence must remain tied to the actual plan, renderer source and sampled pixels.

### Adopt now, while keeping additional spending bounded

Use the already synthesized audio and completed MP4 to produce short local motion
clips around entrances, transitions and important transformations. Review those
alongside contact sheets and source facts. This follow-up is being integrated;
its actual completion belongs in the status record. Extracting a clip is not
equivalent to watching it, and a still-only model endpoint must not be described
as a video/audio reviewer.

Retain exact-input caching and repair only the stage implicated by the defect:
layout repairs should not regenerate accepted scripts, factual script corrections
should invalidate the affected voice/timing, and a changed renderer should refresh
the relevant visual review. Finish existing renders before ordering new creative
variants. Use deterministic local checks and motion excerpts first; add paid
critique only when it can resolve a specific remaining uncertainty. Cache reuse
is a cost control, not permission to reuse stale acceptance evidence.

### Claims not adopted

“Manim beats Remotion” is unsupported as a general claim. Both can produce
programmatic animation; the renderer, authored grammar, correctness checks and
editing decisions must be compared on our actual task. No engine benchmark or
migration is justified by these briefs.

Four to six stills do not replace human review and cannot establish dead stretches,
stutter, audio quality or smooth transitions. A well-designed visual critic can
assist a review; it cannot make the unobserved properties verified. Nor does a
two-second hook establish that the remaining explanation is useful or correct.

An “85/100 passes” threshold has no calibration here. Do not present it as an
industry standard or hide a serious error behind an average. Block concrete
arithmetic, factual, overlap, missing-asset and timing defects; record aesthetic
preferences separately. Extra motion blur, 3D layers, downloaded fonts, music and
15–25 arbitrary scene types are deferred until a specific concept requires them.
The user's no-music dialogue and minimal-canvas preferences remain controlling.
