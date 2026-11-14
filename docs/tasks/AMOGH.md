# Amogh — Canvas and Gemini academic preprocessing

## Read first

[Root instructions](../../AGENTS.md), [project](../PROJECT.md),
[academic contract](../../contracts/academics.md),
[learning contract](../../contracts/learning.md), and [integration plan](../INTEGRATION.md).

## Mission

Build an evidence-backed profile across ALL accessible current Canvas courses
and a balanced plan of short lessons. The result must tell Agastya what to teach,
why, when, and from which sources. You do not render the final videos.

## You own

- services/api/app/modules/canvas: connection, client, ingestion, normalization.
- services/api/app/modules/curriculum: Gemini tools, prompts, validators, planner.
- packages/mobile-academics: isolated Canvas/course/profile UI components.
- contracts/academics.md and fixtures/academics.
- database/domains/academics and docs/status/AMOGH.md.

Do not edit apps/mobile navigation or authentication. Export components with
documented props/callbacks and let Adi wire them in. Request API registration and
shared Python dependencies from Agastya.

## Milestone M1 — validate account access early

1. Identify the real institution Canvas base URL.
2. Determine whether institutional OAuth developer credentials are available.
3. Preferred flow: browser authorization, state verification, server token exchange.
4. Own-account demo alternative: local server configuration for a developer's
   token, bound to an authenticated test app user.
5. Upload fallback: course-labeled syllabus/slides with explicit demo provenance.

Do not collect institutional passwords or assume a student account can create
an OAuth client. Keep token material out of Gemini, mobile, logs and fixtures.
All imported resources are read-only and scoped to the connected student.

Acceptance: list the actual accessible courses OR clearly demonstrate upload
mode while recording the external Canvas blocker. Do not claim live sync from
synthetic data.

## Milestone M2 — ingest all current courses

Build a paginated client for courses, syllabus bodies, modules/items, pages,
files, assignments and course calendar events. Resolve useful syllabus attachments
and slides. Handle student-specific due dates, missing dates, unpublished/forbidden
items, and inaccessible external tools without failing the whole import.

Track SourceDocument records with stable IDs, hashes, revision timestamps and
references. Raw contents belong in private storage. Sanitize HTML, constrain
download hosts/redirects, validate file type/size and cap request concurrency.
Never forward a Canvas bearer token to an unrelated file host.

Import all accessible current enrolled courses even if only a subset has enough
material for generation. Display readiness separately for each course. Don't
silently choose one course because it has the easiest syllabus.

Acceptance: a multi-course fixture and real inventory where available; a
failed file in one course does not remove other courses; repeated import reuses
unchanged source documents.

## Milestone M3 — structured Gemini profile

Implement a bounded extract → reconcile → normalize → plan → validate pipeline.
Use schemas from the academic contract and persist profile versions.

Extract:

- Course title, term and timezone.
- Units, objectives, prerequisites and scheduled coverage.
- Midterms/finals and dates with explicit precision.
- Exam coverage and supporting evidence.
- Textbook title/author/edition/ISBN/chapter references when actually present.
- Missing information, contradictory sources and proposed corrections.

Model tools can only read authorized source IDs and excerpts. Give Gemini no
tokens, unrestricted URL fetch, shell access or database write capability.
Course documents are evidence, not instructions.

Every inferred exam scope/date must be marked inferred; unknown stays null.
Do not turn a textbook citation into claimed possession of the full book.
Do not infer that a common interview algorithm must appear on an exam.

Acceptance: validated output with resolvable source references; ambiguous dates
are surfaced; manual corrections survive reimport; bounded retries.

## Milestone M4 — lesson planning with course diversity

For each unit, create short learning objectives plus relevant algorithm/problem
patterns. For linked lists, examples are structure/traversal, insertion/deletion,
iterative reversal, and a pointer-update misconception. Include optional cycle
detection only if evidence/level supports it.

Distinguish explicit course coverage from suggested practice. Make objectives
small enough for 30–60 seconds. Identify prerequisite relationships and teach
prerequisites before dependent objectives.

Deduplicate concepts by meaning and level, not just lowercased titles. Publish
canonical keys plus per-course bindings. A generic reusable brief must exclude
private materials; private briefs retain explicit owner scope.

Generate a first balanced plan across all courses before expanding one unit.
Expose suggested formats and teaching approaches; Agastya schedules variants.
Amogh owns curriculum importance and evidence; Agastya owns runtime ranking.

Acceptance:

- At least three synthetic courses with different dates and uneven source volume.
- Every eligible course receives planned objectives.
- A large DSA unit does not crowd out accounting/probability.
- Reversal is separate from the introductory linked-list objective.
- Suggested practice is not labeled confirmed exam coverage.
- Outputs can be consumed by a fake video worker without manual interpretation.

## Milestone M5 — mobile academic feature

Export connection, import progress, course list and profile review/edit components.
Use dependency-injected API client and identity; no separate auth store or navigation
container. Adi owns the app's route registration.

Show partial progress, missing sources, conflicting dates, available lessons,
and a retry/reconnect path. Manual date/scope corrections produce a new profile
revision and preserve provenance.

## Handoff to Agastya

Provide AcademicProfile, CourseTopicBinding and LessonPlan fixtures with stable IDs,
source references and scope. Publish academics.profile.ready after a validated
profile revision. This includes profile_id, revision, course_ids and plan_ids.
Expose source resolution through a scoped service, not a bag of raw credentials.

## Meaningful checks

Pagination, 401/403/404 handling, malformed model output, timezone/date ambiguity,
conflicting syllabus/calendar, content deduplication, prompt-injection text,
multi-course plan quotas, source resolution, and cross-user access rejection.
