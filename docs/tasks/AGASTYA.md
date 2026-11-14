# Agastya — generation, learning feedback, recommendations, integration

## Read first

[Root instructions](../../AGENTS.md), [project](../PROJECT.md),
[academic contract](../../contracts/academics.md),
[learning contract](../../contracts/learning.md),
[feed contract](../../contracts/feed.md), and [integration plan](../INTEGRATION.md).

## Mission

Turn lesson plans into a reusable video library, choose what appears in the feed,
and respond to quiz results without starving other courses. Own shared backend
assembly so Adi and Amogh can implement domains without touching the same files.

## You own

- services/api/app/core and main.py when created.
- API modules/videos, modules/recommendations, modules/quizzes.
- services/renderer, including its templates, worker and render assets.
- packages/mobile-learning for isolated quiz/progress components.
- contracts/learning.md, feed.md and shared protocol coordination.
- fixtures/learning and fixtures/feed.
- Shared Python manifests/lockfile; database migration assembly; infra.
- database/domains/learning and docs/status/AGASTYA.md.

Adi owns the mobile application and JS workspace lockfile. Amogh owns academic
schemas. Request changes there through their documented interfaces.

## Milestone G1 — assemble the backend and jobs

Initialize the FastAPI service, configuration, database access, error envelope,
health endpoint, job storage/worker and domain registration. Integrate Adi's
identity adapter into one current-user dependency used by every protected route.
Domains should export routers and service functions without importing main.py.

Start with a durable jobs table and worker leases; no need for Redis/Kafka.
Register domain job handlers without making a new service per task.
Document exact commands, secret names and local service URLs.

Acceptance: a fixture job survives worker restart and duplicate enqueue does not
create duplicate work; an unauthenticated request cannot read private state.

## Milestone G2 — two end-to-end video formats

Implement dialogue_gameplay and visual_explainer first. Reserve template
directories for worked_example, misconception and analogy_story.

Each format needs:

- Starting code/components and an input schema.
- A system/style prompt, teaching structure and timing rules.
- A generic synthetic lesson fixture.
- Narration/voice selection configuration.
- Caption and audio synchronization.
- Render and visual inspection checks.

Claude generates grounded scripts/storyboards and template data; custom animations
may include generated scene code. ElevenLabs generates narration and alignment.
Render portrait videos with readable captions and phone-safe layout.
Character-inspired dialogue is a desired style, not an assumption that specific
character voices are available from the provider.

Generated code runs in an isolated environment without secrets or unrestricted
filesystem/network access, with fixed dependencies and bounded CPU/memory/time.
Model output cannot install packages or execute arbitrary host commands.

Acceptance: two 30–60 second videos for the same objective, with different
explanations and formats, playable on the demo iPhone. Inspect actual output,
not just a successful renderer exit code.

## Milestone G3 — shared catalog and preprocessing

Consume Amogh's lesson plans. Reuse matching ready generic assets before creating
new jobs. Use a semantic compatibility key covering objective, level, language,
notation, style, approach, brief/template versions and access scope.

Publish video metadata only after all required assets are ready. Keep failed jobs
inspectable and retryable without showing broken videos in feeds.
Use an atomic uniqueness boundary for duplicate generation requests.
Build initial coverage across courses before generating many variants of one topic.

Shared videos contain generic teaching content. Raw Canvas sources and private
course bindings do not become public just because the topic is common.
No video generation runs synchronously inside GET /v1/feed.

## Milestone G4 — deterministic recommendation engine

Implement course → objective → variant selection, progressive study density,
recent-exposure penalties, exam urgency, mastery and review scheduling.
Use the proposed settings in PROJECT.md as starting heuristics, not fixed truth.

Start entertainment-heavy, increase learning share with active viewing, and cap
it. Do not increase the ratio because the app is backgrounded. Avoid resetting
the ramp on every API call or brief app reopen.

Balance across courses independently of catalog size. Wrong answers raise topic
priority; choose a different available teaching approach/format after intervening
content. If no variant is ready, queue it and serve something else.

Acceptance using deterministic fixtures:

- Ratio rises across a session.
- Three-course catalog with 20/4/2 videos still gives smaller courses exposure.
- Same video does not repeat immediately.
- A wrong answer changes later unseen ranking, with a reason.
- New render jobs do not delay feed responses.
- If constraints cannot all hold, relaxation is recorded and feed remains usable.

## Milestone G5 — quiz and learning state

Create source-grounded, objective-tagged multiple-choice items. Keep answer keys
server-side. Issue quizzes after sufficient lesson exposure.
Valid submission unlocks regardless of correctness. Idempotency prevents double
grading after network retries. Record misconception tags and objective-level
learning state without treating watch completion as mastery.

Contribute a React Native quiz component via packages/mobile-learning. Adi wires
it into the feed. Define callbacks and response states; no competing app navigation.
Support network retry and ungraded recovery for actual errors.

Increment recommendation_revision after a graded attempt so Adi can drop stale
unseen prefetched cards. Enforce pending quiz state server-side as well as in UI.

## Milestone G6 — integrated demo and operational checks

Wire academic profile events, render publication and unified feed. Keep all course
profiles supported even when only a few demo videos are precomputed.
Provide deterministic synthetic scenarios with linked lists, another CS/math
topic and a different subject.

Show profile evidence, upcoming assessment, mixed feed, progressive ratio,
wrong answer, unlock and alternate explanation. Record live/cached/mock modes.
Prepare already-rendered assets so the demo does not depend on generation latency,
but demonstrate the real generation path separately.

## Milestone G7 — research-backed personalization (post-demo)

Planned work, not implemented or validated. Follow the extension in
[PROJECT.md](../PROJECT.md#planned-extension-research-backed-personalization) and
its [primary research references](../REFERENCES.md#adaptive-recommendations-and-learning).
G4 remains the demo baseline and fallback; G7 must not block G1–G6 acceptance.

### Foundation and evaluation design

- [ ] Inventory existing exposure/quiz events and available ready variants;
  identify gaps without treating mock adapters as live instrumentation.
- [ ] Propose a versioned decision log: context, eligible actions, chosen action,
  selection probability, policy version, occurrence IDs and outcome links.
  Draft owner-scoped Atlas validators/indexes and retention rules; integrate
  through Agastya's migration and contract process before deploying.
- [ ] Coordinate proposed helpfulness/preferences UI with Adi and objective
  difficulty/prerequisite metadata with Amogh. Use synthetic fixtures and local
  fake adapters until those owner interfaces are agreed.
- [ ] Define separate experience and learning metrics, reward/attribution rules,
  delayed recall and transfer questions, baseline assignment, follow-up windows,
  sample-size assumptions and success thresholds before collecting pilot results.
  Record missing assessments separately from incorrect answers.
- [ ] Build deterministic synthetic scenarios for sparse history, uneven course
  inventories, delayed/missing outcomes, duplicate events and unavailable variants.
  Label their results as algorithm mechanics rather than measured learning gains.

### Template personalization pilot

- [ ] Implement a small contextual bandit starting with LinUCB over eligible
  formats/teaching approaches, using pooled starting estimates and bounded
  exploration. Condition preferences on topic and prior knowledge.
- [ ] Keep insertion timing fixed during the initial template experiment; record
  known selection probabilities and verify logged action support before offline
  evaluation. Do not infer causal improvements from deterministic history alone.
- [ ] Verify ownership/ready-asset filtering, course fairness, exploration limits,
  repeat avoidance, retry-safe logging and deterministic fallback under failure.
- [ ] Compare with the fixed baseline using delayed learning and experience
  outcomes. Report uncertainty, difficulty differences and follow-up attrition;
  do not promote a policy based solely on watch time or immediate quiz accuracy.

### Review and insertion experiments

- [ ] Fit and calibrate half-life regression against real retrieval outcomes;
  compare recall prediction and review outcomes with the simple review baseline.
  Preserve neutral unknown mastery and course/exam/prerequisite constraints.
- [ ] Evaluate an action-centered insertion policy against entertainment as the
  baseline action, within progressive density, spacing, coverage and user limits.
  Test that inventory recovery cannot create a wall of lessons and that study
  exposure cannot collapse to zero simply to improve engagement.
- [ ] Run a separate timing experiment with stable template selection. Establish
  retained learning per active minute alongside absolute learning, enjoyment and
  course coverage; document delayed attribution and long-term effects not captured
  by a short-horizon bandit reward.
- [ ] Record actual pilot commands/results, policy versions, limitations and
  rollback criteria in the status file. Claim improved learning only after real
  comparative evidence; retain all phone acceptance checks in INTEGRATION.md.

## Meaningful checks

Job idempotency/leases, cross-user catalog access, no answer-key leakage,
duplicate quiz submission, fairness with uneven inventories, unknown exam dates,
stale feed revision, failed/expired media, and generated-code isolation.

Do not create tests that merely restate constant values. Test observable behavior
and failure boundaries that could break the integrated demo.
