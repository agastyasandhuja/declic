Current implementation note: the policy below records the earlier research experiment.
The user's subsequent reference-video feedback led to continuous reference_v2/v3
formats, then the specific revisions in decision 006. Retrieval-card pauses remain
in guided_v1 only. Gameplay and modest 1.08× dialogue pacing are explicit user
preferences here, not claims that distraction or faster speech improves learning.

The next research pass, covering AI creator workflows, current research and a
minimal visual production rubric, is in
[AI short-form creator workflows](AI_SHORT_FORM_CREATOR_RESEARCH.md). Its proposed
rules are design inputs, not a claim that every rule has been implemented or that
the resulting videos have demonstrated engagement gains.

# Research-informed video generation

November 14, 2026. Scope: the existing linked-list generator and renderer.
These are production changes to test, not measured improvements in engagement or
learning. This is a focused review of relevant papers, not verification of every
platform statistic or reference in the supplied brief.

## Evidence and implementation

| Source inspected | Finding and limitation | Application |
|---|---|---|
| [Guo, Kim & Rubin, 2014, author-hosted full paper](https://up.csail.mit.edu/other-pubs/las2014-pguo-engagement.pdf) | Observational MOOC engagement data favor shorter, planned videos and dynamic explanations. Watch behavior is not a learning assessment; the study does not establish an optimum duration for swipe feeds. | One objective, conversational narration, concrete visual trace; retain the existing 30–60-second contract. Repair long scripts instead of speeding up audio. |
| [Kang et al., 2009, author repository abstract](https://authors.library.caltech.edu/records/9f1n0-x0z52) | Curiosity about trivia was associated with later recall, including surprising answers. The full submitted PDF could not be retrieved. This was not a feed experiment. | Ask a meaningful prediction and resolve it in the same video. The exact hook recipe remains a hypothesis. |
| [Szpunar, Khan & Schacter, 2013, author-hosted full paper](https://www.szpunarmemorylab.com/_files/ugd/30fcde_f8741d913c8d4b66b13b2e8b67c61b9f.pdf) | Two experiments used a 21-minute statistics lecture; interpolated tests supported attention and learning. Their response windows were much longer than ours. | Add recall, real thinking time and separate feedback. Three seconds is a production default, not an experimentally optimal retrieval interval. |
| [Sundararajan & Adesope, 2020, publisher abstract](https://link.springer.com/article/10.1007/s10648-020-09522-4) | Meta-analysis finds interesting but irrelevant details can impair learning, with moderators. Full text is subscription restricted; it does not directly test our Minecraft format. The first author is Sundararajan, not “Sundar.” | Default to concept-only backgrounds; retain gameplay as an explicit comparison. Humor should explain the concept. |
| [Donoghue & Hattie, 2021, full meta-analysis](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2021.581216/full) | Practice testing and distributed practice performed well, with substantial heterogeneity across studies. | Include recall, evaluate delayed retention separately. An ungraded spoken answer does not update mastery. |
| [Zhan et al., 2022, full D2Q paper](https://arxiv.org/html/2206.06003v1) | Duration can confound watch-time ranking. Their solution uses duration-group quantiles and learned predictions, not simply seconds watched divided by duration. | Compare hook survival and completion within duration groups in evaluation. Do not claim completion fraction is causal debiasing or that this change implements D2Q. |

Gruber et al. (2014) was located, but full-text access was blocked; it is not used
for an additional implementation claim. Exact hook-success percentages, platform
ranking summaries, avatar comparisons and ad-load findings are not treated as
verified causal evidence here.

## Implemented policy

New storyboards require five short teaching beats linked to narration segments:
hook → prediction → reveal → retrieval → feedback. Additional demonstration
segments can appear between those beats. The reveal closes the opening question;
the final recall question tests the same objective and gets separate feedback.

The hook has at most eight spoken words and must finish within 3.5 measured seconds.
The prediction has at most fourteen words and must finish by nine seconds. These
are tunable production heuristics. The audio includes two seconds of silence after
prediction and three after retrieval. All subsequent captions, pointer events and
speaker animations share the resulting timeline. Slow/long openings use the
existing bounded script-repair loop; the total stays within 30–60 seconds.

Screen text is capped at 72 characters and twelve words. Short synchronized captions
remain for muted viewing. During questions, answer-bearing code, diagrams, mnemonic
and custom scene are hidden, while the question stays visible through the pause.
The MP4 asks viewers to think or say an answer; it does not display fake tappable
options. The existing interactive app quiz remains a separate authenticated flow.

`VIDEO_BACKGROUND_MODE=concept_only` is the default for new renders; `gameplay`
retains the earlier comparison condition. Dialogue retains both characters and
the trusted pointer trace. The recipe includes policy, system prompt and background
mode to distinguish generated variants. Existing ready assets are not overwritten.

Structural validation cannot establish semantic correctness. The model reviewer
must check narration and screen text against approved facts, ensure questions do
not supply their answers, and verify the reveal/feedback answer the actual questions.
Human content, visual and audio review still gates publication.

## Evaluation before claiming improvement

Compare the same objective, voice, approximate duration and facts across old and
revised scripts; test gameplay separately. Record assignments and exposure counts,
including early swipes, rather than analyzing only people who finish. Report sample
counts and uncertainty. Choose sample size from a pilot baseline and a prespecified
meaningful effect, not an arbitrary handful of demos.

Measure opening survival (for example, at two seconds), visible watch fraction,
completion, immediate quiz results and a different question on the same objective
after a delay. Report results by duration, format and policy version. Delayed recall
is the learning outcome; immediate answers and rewatches are weaker signals.
The current event contract lacks saves/sends, so those measurements cannot be
invented. Missing delayed answers are not automatically incorrect.

This change does not implement a trained ranker, style bandit, adaptive slot rate,
or new spaced-review scheduler. It does not infer mastery from video completion.

## Reference-video rubric

Review the opening, animation/shot timeline, speech rhythm, silence, caption density,
diagram legibility, character delivery, sound design and ending. Compare liked and
disliked examples, then translate differences into a concrete rubric and a comparison
render. Frames establish visual style; audio and timeline inspection are needed
before claiming comparable pacing or delivery. Keep reference media out of Git.

The semantic renderer remains linked-list-specific. Examples alone do not give it
general animation capability. Actual runs and limitations are recorded in
[Agastya's status](status/AGASTYA.md).

## November 14 reference revision

The two additional local references were 33.23 and 44.00 seconds, both 576×1024,
showing matrix multiplication. Inspected temporal contact sheets show stable black
canvases, serif math, color-coded rows/columns, factors moving into a dot product,
and results entering matrix cells. Local ASR yielded only brief nontechnical vocal
fragments; it did not identify spoken mathematical instruction. That supports a
music-led interpretation, but ASR alone does not establish soundtrack genre or quality.
The template uses separately licensed instrumental music, not the source soundtracks.

Concrete revised finance example: hypothetical $1,000, 10% annual compounding,
$1,100 after year one and $1,210 after year two, compared with $1,200 simple interest.
The arithmetic is exact; 10% is an assumption, not an expected return.
[Investor.gov's calculator](https://www.investor.gov/financial-tools-calculators/calculators/compound-interest-calculator)
provides the principal/rate/time/compounding framing. No investment recommendation.

Space hierarchy/filament facts were checked against NASA's
[galaxies overview](https://science.nasa.gov/universe/galaxies/) and
[large-scale structures](https://science.nasa.gov/universe/galaxies/large-scale-structures/).
Rendered structures are illustrative, not measured maps. Distinct geometry and
better hooks remain design hypotheses; no engagement or retention lift is measured.
