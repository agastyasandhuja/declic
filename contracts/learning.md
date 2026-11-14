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
| format_id | dialogue_gameplay / visual_explainer / space_explainer / math_explainer / worked_example / misconception / analogy_story |
| teaching_approach | Explicit short identifier |
| level, language, notation | Reuse compatibility |
| scope | private / shared_generic |
| owner_user_id | Required for private, null for shared_generic |
| status | planned / queued / scripting / voicing / rendering / validating / ready / failed |
| title, learning_goal | Public-safe for shared content |
| duration_seconds | Measured; 30–60 for spoken lessons, 20–60 for music-led math |
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

## Internal teaching beats (November 14)

`Storyboard.teaching_beats` adds five `{kind, segment_id, text}` records: hook,
prediction, reveal, retrieval, feedback. It is optional for historical artifacts
and required for `guided_v1` generation. Timed guided renderer packages include measured
start/speech_end/end seconds and actual thinking pauses. This spoken self-check
is not a QuizCard or graded attempt. Public wire records and the 30–60-second
constraint remain unchanged. See [decision 004](../docs/decisions/004-video-teaching-beats.md).

## Reference-driven presentation v2 (November 14)

`Brief.presentation` originally selected `reference_v2` or `guided_v1` (earlier
five-beat format). `Brief.trace_kind` selects `linked_list_reverse` or `none`;
non-code subjects use `none` and do not fabricate pointer events. Existing stored
boards remain readable when paired with their explicit guided presentation.

Reference storyboards have one `Shot` per narration segment, six to sixteen shots,
with validated camera mode, composition, short labels, approved fact references,
and zero to two requested asset IDs. `ImageRequest` gives a public subject query,
purpose and approved fact IDs; the model never supplies a download URL. The worker
searches NASA/Openverse, offers candidates, downloads from approved CDNs, normalizes
rasters, and requests a visual relevance check. Credits and source/license links
remain in the private local asset manifest; media publication still needs review.

`space_explainer` is a new learning/feed candidate format: narrator-only, at least
four spatial shots and two spatial modes, with NASA imagery. It uses the same MP4
and caption delivery contract. Academics may suggest this format; mobile consumes
an ordinary video. No navigation or authentication interface changes are required.
`VIDEO_BACKGROUND_MODE=auto` chooses parkour for reference dialogue and concept-only
for other formats. `--custom-scene` remains specific to `guided_v1`; reference v2
uses the authored renderer with model-directed shots, not arbitrary scene code.

See [decision 005](../docs/decisions/005-reference-driven-video-templates.md).

### Reference v3 and math (3.0.0)

New Brief defaults to `reference_v3`. This adds photo/scene diversity requirements
without changing existing narration field names or the public playback payload.
`math_explainer` requires `trace_kind=none`. Its original/default matrix topic uses
compatible `matrix_a`, `matrix_b` (2–3 rows/columns, integer entries −9…9).
Matrices are forbidden for other formats. The additive geometry topic below is
the explicit alternative to matrix inputs.
Math uses music and on-screen worked equations; it does not invent spoken segments
or captions. Internal pack includes verified products/sums, timing, `audio_file` and
music attribution. The renderer checks arithmetic again before rendering.
Live v3 generation requires source review (spoken lessons), actual image review,
and rendered-frame inspection. Human review still gates publication. See decision 006.

User-directed math refinement: the minimal matrix format permits 20–60 seconds; spoken formats retain 30–60. The two-by-two demo is 21 seconds. Credits accompany the file instead of occupying the canvas.

### Semantic motion extension (November 14)

The public format IDs, VideoVariant/feed fields and ordinary MP4 delivery remain
unchanged. Updated internal validators accept historical briefs/storyboards through
defaults; new scene packages require the corresponding updated renderer. See
[decision 007](../docs/decisions/007-semantic-motion-video-templates.md).

`Brief.math_topic` defaults to `matrix_multiplication`. The alternative
`pythagorean_rearrangement` requires `pythagorean_sides`, exactly two strict integers
from 1 through 9, and forbids matrix inputs. The sides represent perpendicular
legs, not three supplied side lengths. Trusted code derives the triangle/square
areas and exact endpoint geometry. Matrix plans cannot include Pythagorean sides.
Non-math briefs cannot select the geometry topic or include its side inputs.

`Brief.installment_example` optionally supplies strict integer `unit_price` (4…10000),
`installments` (2…4), and `purchases` (1…3). It is valid only for
`visual_explainer` with `trace_kind=none`; `unit_price` must be divisible by
`installments`. The trusted plan derives payment amounts, total commitments and
remaining balance. These are bounded hypothetical equal-payment illustrations,
not lender-specific payment schedules. Such plans use authored visuals instead of
the four-image requirement for historical photo explainers.

`Shot.motion_scene` defaults to `none`. Non-default modes require `kind=diagram`:

| Family | Modes | Required context |
| --- | --- | --- |
| Payment | `price_tag`, `split_payment`, `stack_purchases`, `payment_calendar`, `total_cost`, `choice_balance`, `receipt` | Validated `installment_example`; no model-provided arithmetic or stock-image requirement |
| Decision | `ticket_purchase`, `ticket_loss`, `future_choice`, `time_loss`, `decision_reset` | The authored $20 nonrefundable ticket/one-hour example, with matching approved facts |

The existing `space_explainer` identifier also supports illustrative biology through
`Shot.space_mode`: `enzyme_hook`, `enzyme_fit`, `enzyme_reaction`, `enzyme_reuse`,
`enzyme_compete`, `enzyme_concentration`, `enzyme_denature`. All-enzyme plans do not
request NASA assets; older space/image modes remain available. Reference-v3 spatial
plans still require distinct demonstrations, not just camera variation. Adi may
optionally label this format **Animated science** without renaming the wire enum.

Current style policy removes diagram backplates in dialogue and keeps its gameplay
muted with narration only. Narrated animation uses shared white single-word speech-aligned pop captions
and essential labels without persistent titles or source footers. Math remains
music-led and minimal. Source/music/image attribution must travel in metadata and
`CREDITS.txt`; the eventual publisher must preserve required attribution in the
description or accompanying credits. These presentation changes do not establish
measured learning/engagement gains or successful iPhone playback.

## Generic semantic diagrams (November 14)

Internal `Brief.visual_strategy` optionally selects `semantic_diagram`; its default
`existing` preserves the authored/photo strategies. The new strategy is valid only
for `visual_explainer`, `reference_v3`, `trace_kind=none`, without an installment
example. It provides a bounded visual path for abstract coursework that does not
require finding four relevant photographs.

Every shot carries `semantic_diagram` with a `mode`, two to four distinct short
`nodes: [{label}]`, and bounded `edges: [{source, target}]` using zero-based node
indices. Labels are at most 24 characters. `comparison` has no edges; `sequence`
has the exact consecutive chain; `cause_effect` connects node zero to every other
node. The latter represents one cause and its stated effects, not arbitrary graph
code. The model cannot supply coordinates, URLs, executable code, hidden numerical
constants, or extra labels. At least two different diagrams must develop the
explanation. Fact references remain on the containing shot.

Both API validation and the isolated renderer enforce these bounds. Claude's
content review checks the labels and implied order/causality against approved
facts, and rendered-frame review still runs before automatic private publication.
A typed diagram is not evidence that a causal claim is true; the existing grounding
and review gates remain required. Existing photo diversity, linked-list traces,
payment arithmetic and specialist scene policies are unchanged.

The API worker and renderer image must be updated together; recipe identity includes
the new authored renderer source. Public video/feed payloads, formats and MP4
playback remain unchanged. Historical published assets remain playable; this change
does not retroactively regenerate them or claim improved learning outcomes.
