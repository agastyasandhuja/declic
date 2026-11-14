# Academic profile and lesson-plan contract

Owner: Amogh. Consumers: generation and recommendations.

## SourceRef and date semantics

SourceRef fields: source_id, course_id, locator, evidence_kind.
locator identifies a page/slide/section/Canvas item; evidence_kind is explicit,
inferred or user_confirmed. Optional excerpt is private and concise.

AcademicDate fields: date (YYYY-MM-DD or null), timestamp (ISO timestamp or null),
timezone (IANA), precision (date / datetime / unknown), evidence_status
(explicit / inferred / user_confirmed / unknown), source_refs.
Never manufacture an exact exam time from a date-only syllabus.

## Core records

| Record | Required fields |
|---|---|
| CanvasConnection | connection_id, user_id, institution_origin, external_user_id, mode, status, last_sync_at |
| SourceDocument | source_id, user_id, course_id, external_id, resource_type, title, storage_ref, content_hash, source_updated_at, fetched_at, scope |
| Course | course_id, user_id, external_course_id, title, term, timezone, import_status, missing_sources |
| AcademicProfile | schema_version, profile_id, user_id, revision, generated_at, course_ids, unit_ids, assessment_ids, binding_ids, lesson_plan_ids, warnings |
| Unit | unit_id, course_id, title, order, coverage_start, coverage_end, objective_ids, source_refs |
| Assessment | assessment_id, course_id, title, kind, scheduled, scope_status, covered_objective_ids, source_refs |
| CanonicalObjective | objective_id, canonical_key, title, subject, level, language, notation, prerequisites, learning_goal |
| CourseTopicBinding | binding_id, user_id, course_id, unit_id, objective_id, coverage_status, assessment_ids, source_refs |

Status values:

- CanvasConnection.mode: oauth / developer_token / upload.
- Connection status: connected / reconnect_required / disconnected / error.
- Course.import_status: queued / fetching / extracting / planning / ready /
  needs_review / partial / error.
- Assessment.kind: midterm / final / quiz / assignment / other.
- Assessment.scope_status: explicit / inferred / user_confirmed / unknown.
- Binding.coverage_status: explicit / inferred / suggested_practice.
- Source scope: private. Canonical records contain no private sources.

Canonical key example: cs.dsa.linked_list.reverse.iterative.intro.en.
Notation includes programming language and conventions where relevant. Canonical
keys are proposed matching aids; deduplication must validate semantic compatibility.

## LessonPlan

Fields:

- schema_version, plan_id, user_id, profile_id, profile_revision, course_id.
- revision, status (draft / validated / superseded), created_at.
- requests: array of LessonRequest.

LessonRequest fields:

| Field | Type / rule |
|---|---|
| lesson_request_id | Stable unique request ID |
| objective_id, binding_id | Canonical target and private course context |
| title, learning_goal | One narrow teachable goal |
| prerequisite_objective_ids | Array of IDs |
| source_refs | Supporting private source references |
| evidence_status | explicit / inferred / suggested_practice / user_confirmed |
| exam_scope_status | explicit / inferred / user_confirmed / unknown |
| assessment_ids | Relevant assessments; empty allowed |
| importance | core / supporting / optional |
| suggested_formats | Format IDs from learning contract |
| teaching_approaches | e.g. pointer_trace, misconception, analogy |
| target_duration_seconds | 30–60 |
| desired_variant_count | Positive bounded integer; initial default 2 |
| generic_brief | Generic explanation brief or null |
| private_context_ref | Authorized source-context reference or null |
| scope | private or shared_generic_candidate |
| warnings | Array; includes missing or conflicting evidence |

shared_generic_candidate is not publication approval. The video service validates
that reusable outputs contain no private course content before marking them shared.
User-specific course bindings and dates remain private in all cases.

## Routes

- GET /v1/canvas/connection → connection summary, no secrets.
- POST /v1/canvas/connect → institution identifier; returns authorization_url/state
  reference for configured OAuth flow. Server binds state to the current user.
- GET /v1/canvas/callback → OAuth callback; validates state and returns to app
  through a configured link containing no Canvas token.
- DELETE /v1/canvas/connection → disconnect and stop future sync.
- POST /v1/canvas/sync → 202 job_id; all accessible current enrolled courses.
- POST /v1/academics/uploads → validated course-labeled file upload/job reference.
- GET /v1/academics/jobs/{job_id} → progress plus per-course statuses.
- GET /v1/academics/profile → latest version and associated course/unit summaries.
- PATCH /v1/academics/profile → corrections plus expected_revision.
- GET /v1/academics/courses/{course_id}/plan → validated LessonPlan.

Developer-token mode is server-configured for a bound demo user, not a public
credential-collection endpoint. Callback is authenticated by stored OAuth state,
not by requiring a mobile bearer token on Canvas's redirect.

## Public service interface

get_profile(user_id), get_course_bindings(user_id), get_validated_plans(user_id),
resolve_source_context(user_id, source_refs), apply_corrections(user_id, revision, changes).

Publishing a validated revision emits academics.profile.ready. Consumer rejects
superseded profile revisions. Reimport must preserve current manual overrides.

## Fixture requirement

At least three courses: DSA linked lists, probability, and accounting. Include
one explicit exam, one date-only assessment, one unknown scope, a suggested
algorithm, a missing slide deck, and a conflicting date warning. Source IDs must
resolve within the synthetic fixture set. Do not fabricate actual UMass course data.

## Local development adapter

The owner routers compose through Agastya's `create_app(domain_routers=...)`.
Both use the shared verified principal, except the OAuth callback, which uses
the single-use state. The routes share one local jobs instance.

- `POST /v1/canvas/connect` accepts `{"institution":"https://canvas.example"}`
  for the server-configured origin. `authorization_url` carries the state;
  the callback redirects to the configured app URL without credentials.
- `POST /v1/canvas/sync` and `POST /v1/academics/uploads` require
  `Idempotency-Key`. The local upload adapter accepts JSON `course_label`,
  `filename`, and UTF-8 `content` for `.txt` or `.md` (up to 30,000 characters,
  subject to core request limits). Job states are `queued`, `running`,
  `succeeded`, and `failed`.
- `PATCH /v1/academics/profile` accepts `expected_revision` and `changes`, an
  array of `assessment_id` plus `date` and/or `scope_status`. Omit a field to
  preserve it. Explicit `date: null` records the student's correction to an
  undated assessment. Corrections supersede the current plans until reimport
  and replanning. Local override matching uses course plus normalized assessment
  title. If extraction omits or renames the assessment, the correction stays
  stored and applies when the original identity reappears.
- The existing local pipeline uses source-ID strings as compact `source_refs`.
  `resolve_source_context` accepts these strings or a structured `SourceRef`
  with a matching course ID and returns only that owner's current excerpts
  and metadata. HTTP profile responses omit the private excerpt snapshot.

The local profile snapshot stores the ready-event payload alongside its
validated plans. Shared outbox publication and persistent job registration
are integration handoffs. The local router does not expose provider secrets,
raw blobs, or internal events.

## Canvas timeline eligibility

Canvas-backed lesson requests may include `timeline_topic`, the topic supported
by a cited upcoming assessment. For this personalized feed, the academic reader
requires a current linked target and rechecks eligibility against the request-time
clock. An offset-bearing deadline expires at its actual instant. A date-only
deadline stays eligible through the course-local day. Unknown and conflicting
dates do not qualify as upcoming. The next dated exam takes priority when its
covered topics are supported. Earlier dated coursework remains eligible alongside that exam. Another dated assignment can supply a
topic when its title or supported coverage names one. A generic assignment or exam
title alone does not establish any topic. Legacy Canvas lesson requests without
a timeline topic require reimport before feed use.

## Model-directed course reading

The backend supplies Gemini a per-course inventory of student-visible module
outlines, Pages, files, assignment descriptions, calendar events and the syllabus
overview. Inventory entries include source IDs and module labels where Canvas
provides the association. Gemini can request IDs in one bounded selection round.
The backend resolves only IDs belonging to the current course and user, then
passes text and eligible PDF, PNG and JPEG attachments to extraction. PPTX is
read as slide text. Direct Canvas deadlines and corroborated text evidence still
govern lesson eligibility. Vision-only date or scope claims require separate
verification before they can drive the feed.


The Canvas planner prepares future topic bindings directly from named coursework
and verified assessment coverage. The service exposes the nearest eligible exam
plus up to four earlier coursework targets, or up to five coursework targets
when no exam has known coverage. Date-only values require a known course timezone.
A shared topic retains all supporting upcoming assessment IDs and expires after
its final eligible target passes. Both service plan reads and feed candidate
reads apply this policy. The upload fallback retains its existing planning behavior.

Canvas requests are topic handoffs. Existing duration and suggested-format fields
remain defaults for compatibility. The video owner determines the narrow teaching
objective and generation brief. Fresh Canvas synchronization is required to detect
instructor schedule changes or withdrawn material.


## Source-backed practice fallback for the integrated demo

When an enrolled course has no teachable upcoming assessment topic, its latest
imported units may contribute up to three suggested-practice requests. Each
request must cite an accessible lecture Page or file from that course's current
source inventory. Assessment, exam, answer-key, and solution material alone does
not qualify. The service rechecks the unit and source references when reading plans and feed
candidates. A due assignment without teaching evidence does not suppress grounded
practice; practice retains lower priority alongside newly announced assessments.

These requests have no assessment IDs or timeline topic, use unknown exam scope,
and receive no exam urgency or current-unit ranking bonus. No date or current-week
claim is inferred. Expired assessment-derived requests remain excluded; reconnect
or reimport is still needed to discover newly published course material. This is
an additive fallback for the requested all-course demo, overriding the earlier
blanket exclusion of otherwise grounded material without a known deadline.


Planning with a source resolver requires extracted conceptual page/file text.
Assessment labels, calendars, navigation links, schedules, and due dates provide
priority evidence only, never approved teaching facts or quiz content. Chapter
labels may select matching chapter material but cannot supply its explanation.
Preparation returns `unavailable` with `INSUFFICIENT_TEACHING_EVIDENCE` before
model work when no teaching excerpt exists, or when a model returns placeholder
or administrative facts. No quiz or video job is published in that case.

When extracted lecture text exists but the course map has no supported lesson,
one bounded planning call may recover up to three practice concepts from five
authorized excerpts. Each concept requires two distinct verbatim teaching quotes
from those excerpts. The resulting source-backed units are persisted for service
and feed eligibility checks, with unknown exam scope and no assessment dates.
Learning outcomes describe teaching intent, not facts; neither outcomes nor
syllabus-only material qualify. Short formula and wrapped lecture lines remain
available to the model.
