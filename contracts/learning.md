# Video generation, quizzes and learning-state contract

Owner: Agastya.

## Generation input

Consume validated LessonRequest records from [academics](academics.md).
Resolve private context with the current owner scope. A generation request is a
job, not a synchronous feed operation.

GenerationKey components: objective_id, level, language, notation, format_id,
teaching_approach, brief_hash, template_version, scope, and owner_id for private
content. It must be stable across retries and protected by atomic uniqueness.
Version narration/model decisions as part of the rendered artifact metadata.

## VideoVariant

| Field | Type / rule |
|---|---|
| schema_version, video_id | "1", stable ID |
| objective_id, lesson_request_id | Target and generating request |
| format_id | dialogue_gameplay / visual_explainer / worked_example / misconception / analogy_story |
| teaching_approach | Explicit short identifier |
| level, language, notation | Reuse compatibility |
| scope | private / shared_generic |
| owner_user_id | Required for private, null for shared_generic |
| status | planned / queued / scripting / voicing / rendering / validating / ready / failed |
| title, learning_goal | Public-safe for shared content |
| duration_seconds | Measured; 30–60 for ready lesson |
| asset_id, playback, thumbnail_url, captions_ref | Ready asset metadata; otherwise nullable |
| template_version, brief_hash, generation_version | Reproducibility |
| quality_checks | Structured checks, reviewer status and failures |
| created_at, ready_at | Timestamps; ready_at nullable |

Private source citations are stored in course bindings and authorized detail
responses, never in globally shared manifests. Only ready variants are feed-eligible.

## Internal RenderJob

job_id, schema_version, generation_key, template_id, template_version,
scene_data_ref, optional_scene_code_ref, audio_assets, alignment_ref,
caption_data_ref, local_asset_manifest, output_spec, timeout_seconds.

All input refs resolve to staged allowed files in an isolated job workspace.
No arbitrary path traversal, arbitrary remote URLs, provider secrets or database
credentials. RenderResult contains job_id, state, output_assets, measured_duration,
frame_check_refs and sanitized diagnostics. Caller uploads and publishes output.
The renderer has no direct authorization to mark a video globally shared.

## Quiz records

QuizDefinition server-side: quiz_id, revision, objective_ids, prompt, options,
correct_option_id, explanation, misconception_by_option, source_refs, scope.

QuizCard client-side: quiz_instance_id, quiz_id, revision, objective_ids, prompt,
options [{option_id, text}], related_video_ids.

Do NOT include correct_option_id, answer-bearing explanation or answer-revealing
misconception tags in the pre-submission payload.

QuizAttempt: attempt_id, user_id, session_id, quiz_instance_id, selected_option_id,
correct, submitted_at, objective_ids, learning_revision.
Only the server sets correct. A quiz instance accepts one effective answer;
retries return the original result rather than creating another attempt.

TopicLearningState: user_id, objective_id, mastery_estimate, correct_count,
incorrect_count, last_attempt_at, last_reviewed_at, next_review_at,
misconception_tags, revision. New mastery is unknown/neutral, not zero.

## Routes

- GET /v1/learning/videos/{video_id} → authorized variant detail.
- GET /v1/learning/videos/{video_id}/playback → fresh playback metadata.
- GET /v1/learning/progress → current user's objective/course progress.
- POST /v1/quizzes/{quiz_instance_id}/answers → session_id, selected_option_id;
  Idempotency-Key required.

Answer response: attempt_id, accepted, correct, explanation, scroll_unlocked,
learning_revision, recommendation_revision. For any valid new answer,
accepted and scroll_unlocked are true regardless of correctness.

- POST /v1/quizzes/{quiz_instance_id}/recover → session_id, reason, client_event_id.
  Reasons are content_error or submission_unavailable; server records ungraded
  recovery. It cannot fabricate a graded answer or increase mastery.

No client endpoint accepts arbitrary scene code or an arbitrary correct answer.
Administrative generation endpoints, if needed, are separate authenticated
development interfaces disabled in normal client builds.
