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

## Meaningful checks

Job idempotency/leases, cross-user catalog access, no answer-key leakage,
duplicate quiz submission, fairness with uneven inventories, unknown exam dates,
stale feed revision, failed/expired media, and generated-code isolation.

Do not create tests that merely restate constant values. Test observable behavior
and failure boundaries that could break the integrated demo.
