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
