# Technical requirements: lesson video generation

Status: proposed implementation specification; no generation integration has been implemented or validated by this document.

Owner: Agastya. Written November 13, 2026, America/New_York.

Scope: video generation, video boilerplates, Claude generation pipeline, ElevenLabs narration and captions, and rendering. This document expands [PROJECT.md](PROJECT.md) and [Agastya's task guide](tasks/AGASTYA.md). The existing [academic](../contracts/academics.md), [learning](../contracts/learning.md), and [shared](../contracts/README.md) contracts remain authoritative. New records below are proposed internal schemas, not changes to Amogh's wire contract.

## 1. Outcome and boundaries

Given a validated, authorized lesson request, produce a 30–60 second portrait video that teaches one narrow objective, has intelligible narration and synchronized captions, and is playable in the iPhone feed. Reuse a compatible ready video when possible. Generation is asynchronous and never blocks entertainment playback or a feed request.

The first release supports two formats for the same learning objective:

1. `dialogue_gameplay`: Minecraft parkour fills the background. Peter and Stewie appear at the bottom. Peter asks questions and makes plausible mistakes; Stewie responds with sarcastic corrections and a useful explanation. Captions appear in the middle. Different videos use varied gameplay maps and segments.
2. `visual_explainer`: narration accompanies topic-specific coded animations, diagrams, code, and worked state changes. Claude can generate custom scene code using a controlled Remotion foundation; this must not collapse into the same generic text slideshow for every subject.

The requested character presentation is a product target. Actual voice IDs, artwork, gameplay recordings, and their suitability for this use have not been selected or verified. Placeholder assets can unblock implementation, but must be labeled in demo evidence and cannot count as verification of the requested character experience.

Out of scope for this TRD: Canvas fetching, Gemini course planning, mobile navigation/authentication, feed ranking, quiz submission/mastery, production-scale media acquisition, fully generative Minecraft footage, and photorealistic character animation. A separate quiz workflow may consume the approved brief later; this pipeline does not emit answer keys into video manifests.

### 1.1 Confirmed behavior versus proposed defaults

| Item | Classification | Requirement/default |
|---|---|---|
| Duration and device | Confirmed | 30–60 seconds, portrait, actual iPhone playback |
| Timing of generation | Confirmed | Preprocess in background; no generation on swipe |
| Two initial formats | Confirmed | Dialogue/gameplay and topic-specific visual explainer |
| Dialogue arrangement | Confirmed | Minecraft background, characters at bottom, captions in middle |
| Dialogue dynamic | Confirmed | Peter questions; Stewie teaches with sarcastic responses |
| Automated Claude access | Confirmed | API-authenticated automation; no manual terminal step required |
| Agent harness | Proposed implementation | Python Claude Agent SDK with an API key |
| Renderer | Existing stack proposal adopted here | Remotion in isolated Node/Chromium execution |
| Narration | Existing stack proposal adopted here | ElevenLabs, one segment per speaker turn or coherent narration beat |
| Resolution/frame rate | Proposed | Final 1080 × 1920, 30 fps; preview 540 × 960 |
| Character animation | Proposed | Sprites/expression states with amplitude-driven mouth movement |
| Background inventory | Proposed | Start with 5–10 recordings across distinct maps/themes |
| Quality review | Proposed demo gate | Human review for every demo lesson in addition to automated checks |

## 2. Architecture and trust boundaries

Use the existing modular FastAPI backend, persistent jobs table, Python worker, and internal renderer. This design adds no separate queue platform, agent hosting platform, or public rendering service. The Agent SDK is a worker dependency, not a new network service.

```mermaid
flowchart TD
    A["Authorized validated lesson request"] --> B["Resolve brief and check catalog"]
    B --> C{"Compatible ready variant?"}
    C -->|Yes| D["Attach existing video"]
    C -->|No| E["Persist generation job"]
    E --> F["Claude: script and storyboard"]
    F --> G["Validate facts and structure"]
    G --> H["ElevenLabs: speech and alignment"]
    H --> I["Build measured timeline and captions"]
    I --> J{"Format"}
    J -->|Dialogue| K["Populate gameplay and character template"]
    J -->|Visual explainer| L["Claude: implement timed scenes"]
    K --> M["Isolated compile and preview"]
    L --> M
    M --> N{"Quality checks"}
    N -->|Repairable| O["Bounded Claude repair"]
    O --> M
    N -->|Passed| P["Final render and media validation"]
    N -->|Budget exhausted| Q["Failed, inspectable job"]
    P --> R["Upload and publish ready variant"]
```

| Boundary | May access | Must not access or do |
|---|---|---|
| API/domain services | Verified app identity, authorized plans, catalog/job storage | Accept caller-selected ownership, run rendering inline |
| Trusted worker/controller | Provider credentials, authorized context, stage records, object storage | Execute generated JS/TS/Python on the worker host |
| Claude agent session | Approved brief, template documentation, scoped generated files, preview reports | Database/storage credentials, arbitrary shell, unrelated repository/user files, unapproved network tools |
| ElevenLabs adapter | Exact approved narration and configured voice settings | Raw syllabus, Canvas tokens, source documents it does not need |
| Renderer sandbox | Staged local media, generated scene sources, immutable dependencies | Provider/app credentials, host filesystem, network egress, Docker socket |
| Publisher | Validated output assets and authoritative access scope | Trust a model's claim that content is shared or ready |

The Agent SDK process necessarily talks to the model provider. The no-egress requirement applies to generated-code execution, including compilation, composition discovery, previewing, and final rendering. These operations all run in the separate sandbox. SDK tool restrictions are not a substitute for that sandbox.

## 3. Input contract and brief resolution

### 3.1 Consume the existing academic interface

Accept only a `LessonRequest` belonging to a validated `LessonPlan` and current authorized profile revision. The trusted caller supplies identity through the common current-user dependency or a trusted job actor, never a public JSON `user_id`.

Before enqueueing:

1. Verify the plan and binding belong to the actor; check plan/profile revision and status.
2. Validate objective, supported format, target duration, and bounded variant count.
3. Resolve source references through Amogh's authorized resolver. Missing or conflicting evidence must remain explicit.
4. Resolve canonical level, language, notation, and prerequisites. If the academic service does not yet expose canonical-objective lookup, record an interface request and use a synthetic adapter; do not guess these from a course title.
5. Select a generic-only or private source path. `shared_generic_candidate` is not permission to publish.
6. Build an immutable `GenerationBrief`, calculate its content hash, and check for reuse.

The generic path receives only a reviewed generic brief and generic supporting material. Do not mix private excerpts into a supposedly generic job and rely on a final text filter to remove them. If private context is needed, select private scope and keep derived artifacts owner-scoped.

### 3.2 Proposed internal GenerationBrief v1

All records use `schema_version: "1"`. Fields marked internal are never model-selected or included in shared playback manifests.

| Field | Type and semantics |
|---|---|
| `brief_id`, `brief_revision` | Immutable internal identifier and revision |
| `lesson_request_id`, `objective_id` | Existing contract identifiers |
| `origin` | Internal plan/profile IDs and revisions, actor/owner, binding reference |
| `title`, `learning_goal` | One narrow objective, not an entire unit |
| `subject`, `level`, `language`, `notation` | Canonical compatibility metadata |
| `prerequisite_objective_ids` | Existing IDs; may be empty |
| `assumed_knowledge` | Short learner-facing prerequisite descriptions |
| `must_cover`, `must_not_claim` | Bounded lists of content requirements and unsupported claims |
| `approved_facts` | Fact IDs, concise statements, support references, evidence status |
| `example_spec` | Structured example input, expected result, invariants or worked states |
| `misconceptions` | Plausible mistakes with approved corrections |
| `format_id`, `teaching_approach` | One selected format and one explicit instructional approach |
| `target_duration_seconds` | 30–60 inclusive |
| `scope` | Internal effective scope: private or reviewed generic candidate |
| `context_refs` | Internal references to authorized immutable context; not arbitrary paths/URLs |
| `warnings` | Missing/ambiguous context and restrictions carried forward |
| `template_version`, `prompt_bundle_version`, `generation_version` | Pinned dependencies for this request |
| `brief_hash` | Hash of canonical teaching content and relevant constraints |

The model-visible projection omits actor, course, binding, assessment dates, storage locations, and credentials unless a private lesson specifically needs some of that content. Even then, share only the minimum approved teaching context.

Example model-visible teaching payload (illustrative; not a complete upstream `LessonRequest`):

```json
{
  "schema_version": "1",
  "title": "Reverse a singly linked list",
  "learning_goal": "Explain why next must be saved before reversing each link",
  "subject": "computer_science",
  "level": "introductory_undergraduate",
  "language": "en",
  "notation": "Python",
  "assumed_knowledge": ["A node contains a value and a next pointer"],
  "must_cover": [
    "Save current.next before changing it",
    "Set current.next to previous",
    "Advance previous and current",
    "Return previous as the new head"
  ],
  "must_not_claim": ["This algorithm is confirmed exam content"],
  "example_spec": {
    "input_values": [1, 2, 3],
    "expected_output_values": [3, 2, 1],
    "invariant": "Retain access to the unprocessed suffix"
  },
  "misconceptions": [
    {"mistake": "Overwrite next first", "correction": "Save the successor first"}
  ],
  "format_id": "visual_explainer",
  "teaching_approach": "pointer_trace",
  "target_duration_seconds": 45
}
```

### 3.3 Reuse and identity

Use the learning contract's `GenerationKey`: objective, level, language, notation, format, teaching approach, brief hash, template version, scope, and owner for private content. Canonicalize serialization before hashing; include an effective recipe version inside the template version when prompt/voice/runtime changes are intentionally supposed to force new generation. Record all exact recipe versions separately in artifact metadata.

Two independent users may reuse an approved generic variant. Private content must never deduplicate across owners. An identical retry returns the existing job or ready asset. A visual-only gameplay change must not silently defeat semantic lesson reuse: ordinary requests prefer the existing video; deliberate creative variants require a distinct versioned recipe selection.

Use an atomic database uniqueness boundary on generation identity. Per-request mappings attach reused videos to each learner's private course binding without mutating the shared asset's originating metadata. Do not expose another user's `lesson_request_id` through a shared playback response. Any new shared response projection must follow the contract change protocol before implementation.

## 4. Internal artifacts and versioning

Persist each successful stage as an immutable artifact. A stage record includes input digest, output digest, attempt, schema version, recipe versions, UTC timestamps, and sanitized outcome. Store large payloads privately in object storage or local development artifact storage; database rows hold references and hashes.

| Artifact | Required contents |
|---|---|
| `ScriptStoryboard` | Objective, format, ordered segments, scenes, fact coverage, symbolic animation cues |
| `NarrationSegment` | Stable segment ID, speaker role, exact spoken text, display-text mapping, allowed delivery metadata |
| `AudioSegment` | Segment/text hash, voice/model/settings version, asset ref, decoded duration, character alignment, alignment source |
| `TimedLesson` | Ordered audio offsets, global words/captions, resolved cues, scene intervals, final duration/fps/frame count |
| `ScenePackage` | Validated template data; optional scene sources; entry point; checksums; dependencies fixed by template |
| `BackgroundSelection` | Recording ID/version, approved range, trim start/end, crop, playback rate, selection seed |
| `QualityReport` | Check IDs, pass/fail/needs-review, measurements, frame refs, human review status and revision |
| `GenerationManifest` | Input lineage, exact recipes, selected assets, final hashes, measured media metadata, scope and QC refs |

Every change to spoken text invalidates audio for that segment and all downstream timing, scene bindings, previews, and review approval. A voice change also invalidates its audio and downstream timing. A purely visual edit retains narration but invalidates scene outputs and visual review. Asset approval must apply to the exact output digest, not merely the job ID.

### 4.1 ScriptStoryboard structure

| Record | Fields and validation |
|---|---|
| Segment | `segment_id`, `speaker_role`, `spoken_text`, `display_text`, `delivery`, `fact_ids`; bounded text and supported speaker |
| Scene | `scene_id`, `segment_ids`, `visual_intent`, `entities`, `events`, `takeaway`; no invented absolute speech times |
| Event | `event_id`, semantic action, entity refs, start/end cue references; unique IDs and resolvable entities |
| Cue | `segment_id`, exact phrase, zero-based occurrence, start/end edge, optional bounded offset; ambiguity is invalid |
| Coverage | Mapping from every must-cover item to supporting segment/scene IDs |

Delivery is an allowlisted enum such as neutral, curious, sarcastic, or emphatic. It is an instruction to our adapter, not arbitrary provider markup. Unsupported delivery features are omitted and logged; do not speak stage directions aloud.

### 4.2 Example storyboard slice

Illustrative partial output, not a complete 30–60 second lesson:

```json
{
  "schema_version": "1",
  "segments": [
    {
      "segment_id": "seg_01",
      "speaker_role": "peter",
      "spoken_text": "So I just point the first node backward?",
      "display_text": "So I just point the first node backward?",
      "delivery": "curious",
      "fact_ids": []
    },
    {
      "segment_id": "seg_02",
      "speaker_role": "stewie",
      "spoken_text": "No, you nitwit. Save the next node first, or you lose the rest of the list.",
      "display_text": "No, you nitwit. Save the next node first, or you lose the rest of the list.",
      "delivery": "sarcastic",
      "fact_ids": ["fact_save_successor"]
    }
  ],
  "cue": {
    "segment_id": "seg_02",
    "phrase": "Save the next node first",
    "occurrence": 0,
    "edge": "start",
    "offset_ms": 0
  }
}
```

Both formats use the same segment/cue representation. `visual_explainer` normally uses the `narrator` speaker role; it does not require a dialogue script.

## 5. Boilerplate package requirements

A boilerplate is a versioned render foundation plus generation instructions, not just a prompt or a single video. Pin its dependencies and provide an offline-capable renderer image.

Each format package must contain:

- A manifest: format ID, template version, input schema reference, output target, supported components and asset roles.
- An immutable root composition and validated props schema.
- Shared layout tokens, font assets, caption components, transitions, audio scheduling, and safe-area helpers.
- A format prompt covering narrative structure, visual requirements, allowed changes, and forbidden assumptions.
- A component reference with inputs, timing conventions, and one complete manually authored example.
- Synthetic valid and invalid inputs, an expected visual checklist, and representative golden frames.
- Commands for validation, still previews, low-resolution preview, and final render once the runtime exists.

No template may fetch fonts or media during rendering. Fixed assets are staged before the sandbox starts. Generated sources may not change the root composition, dependency manifest, compiler configuration, tool wrappers, validation rules, or publication code.

### 5.1 Dialogue/gameplay specification

**Layout at 1080 × 1920, proposed initial coordinates:**

| Layer | Initial bounds/behavior |
|---|---|
| Gameplay | Full frame, cover crop; parkour route remains visible near center |
| Optional concept overlay | Upper region approximately y=160–700; small and used only when it aids teaching |
| Main captions | Middle region approximately x=80–920, y=760–1120; maximum two lines |
| Peter | Lower left, approximately x=80–470, y=1190–1660 |
| Stewie | Lower right, approximately x=530–920, y=1190–1660 |
| App-safe padding | Reserve rightmost ~120 px and bottom ~220 px for app controls; reconcile with Adi before device signoff |

Coordinates are configurable defaults, not a confirmed mobile overlay contract. Caption font starts around 64 px, with a proposed minimum of 54 px at full resolution. Use high-contrast fill plus stroke/shadow. Shorten caption groups rather than shrinking text indefinitely. Speaker labels/colors supplement, not replace, character identity.

**Narrative structure:** Peter opens with a concrete question or wrong assumption. Stewie corrects it, explains one idea, and demonstrates a small example. Peter asks a follow-up that exposes the common pitfall. Stewie ends with a concise correct takeaway. Proposed speaking balance is 20–35% Peter and 65–80% Stewie. Humor must not consume most of the lesson or ridicule the learner. Vary sarcasm; do not repeat the same insult in every clip.

**Character behavior:** both characters remain visible unless a layout exception is explicitly authored. The active speaker uses an expression state and mouth movement driven by that speaker's audio envelope; the silent character returns to idle. A proposed starting asset pack has idle, speaking, confused, and annoyed poses, with open/closed mouths where practical. This is stylized speaking animation, not phoneme-accurate lip sync. Frame changes must stop during actual speech pauses. Portrait images, expression assets, and speaker mappings are pinned to the recipe.

**Generation surface:** Claude emits structured dialogue, expressions, emphasis, and optional educational overlay data. It does not generate arbitrary code for the gameplay layer or rewrite character positioning. Layout remains stable across videos.

### 5.2 Gameplay sourcing and selection

Prepare a small approved source library by recording original Minecraft parkour or obtaining recordings with explicit reuse permission. Do not scrape arbitrary video URLs at generation time. Track attribution/permission evidence as private catalog metadata. Source selection remains unverified until actual recordings have been acquired and inspected.

Initial target: 5–10 recordings across sky, forest, snow, colorful obstacle, and Nether-style maps; preferably several minutes each. Capture without HUD, chat, watermarks, or music. Prefer portrait-friendly framing or high-resolution landscape source that retains a clear route after cropping. Never claim a low-resolution crop becomes native 1080p merely because the export dimensions are larger.

`BackgroundAsset` fields: asset ID, immutable version/hash, storage ref, source width/height/fps/duration, theme/map tags, default crop/focal point, approved continuous intervals, excluded intervals, approval status, provenance reference, and attribution requirements. Store recordings outside Git. Repository fixtures contain synthetic metadata or tiny reproducible test assets only.

Selection algorithm:

1. Filter to approved assets with a continuous interval long enough for measured lesson duration plus trim tolerance.
2. Prefer a different map/theme from recent generated dialogue videos; then prefer a less-used recording and segment.
3. Choose a start point inside a valid interval using a stored seed; reserve/persist the selection before rendering.
4. Record trim, crop, and source checksum. Retries use the stored selection.
5. If no range fits, try another approved recording; use an explicitly approved loop/cut only as a documented fallback. Otherwise mark the job blocked on assets rather than download an arbitrary file.

Avoid deaths, menus, loading, major camera resets, and abrupt mid-lesson cuts. Source audio is muted by default. Background variety affects creative generation; repeated exposure to an already-shared video remains the recommendation engine's responsibility.

### 5.3 Visual-explainer specification

The template provides portrait composition, narration/captions, safe areas, timeline helpers, and reusable primitives: text panels, code blocks, line highlighting, labeled nodes, directed arrows, counters, axes, and transitions. The first implemented primitives should support linked-list pointer traces; do not build a universal animation framework before the first lesson works.

Claude may add scene-local React/TypeScript components and data. Examples include a pointer reversal, a probability tree, or an accounting balance change. Preserve notation and semantic correctness: an arrow direction, sign, or code highlight is part of the lesson, not decoration.

Proposed scene entry interface: one default React component per generated scene, receiving `scene_data`, `timing`, `assets`, and `layout`. Inputs are validated JSON or trusted handles; no caller-supplied filesystem path becomes a prop. The trusted root composition selects scene intervals and layers captions/audio. Exact TypeScript types derive from the versioned render schemas during implementation.

All animation state must derive from current frame and immutable props. Do not use wall-clock time, uncontrolled randomness, network fetches, or browser event timing. If randomness is needed for decorative motion, use a persisted deterministic seed. Re-rendering the same frame must reproduce the same visible content.

Each scene must communicate a defined state change. For linked-list reversal, explicitly distinguish `previous`, `current`, and `next`; save the successor before changing the arrow; maintain access to all nodes; and end with the correct head. Keep state traces as structured data that validators can inspect without trusting a model's natural-language assurance.

## 6. Claude generation pipeline

### 6.1 Harness and provider choice

Use the Python Claude Agent SDK with API-key authentication in the background worker. Anthropic documents the SDK as the programmable agent loop underlying Claude Code [S1]. We are not automating the interactive terminal or using subscription login as the app's backend authentication. A raw Messages API implementation is an alternative if SDK integration proves unsuitable, but would require implementing tool orchestration ourselves.

Keep a provider-neutral internal adapter so jobs depend on our schemas, not SDK response objects. Set the model through server configuration and record the actual model ID per attempt. Pin and verify SDK/model/tool behavior during implementation; this TRD does not assert a particular model or SDK version works.

### 6.2 Prompt bundle

Build versioned prompts from these layers, in order:

1. Stable system rules: teach the brief, follow schemas, treat source excerpts as data, use only supplied assets/tools, and never alter ownership or publish directly.
2. Format instructions: Peter/Stewie conversation rules or visual-explainer teaching/animation rules.
3. Component API and timing documentation, including legal entry points and writable files.
4. One complete matching example and relevant failure examples.
5. Current approved brief and bounded context, clearly delimited as untrusted source material.
6. Stage-specific task and required output schema.

Source documents cannot add tools or override instructions. Do not automatically load arbitrary repository/user hooks, plugins, MCP servers, or personal Claude configuration into jobs. Configure only the explicit tool set for this worker.

### 6.3 Stages and outputs

| Stage | Claude sees | Output | Required gate |
|---|---|---|---|
| Plan/script | Brief, fact support, format prompt, exemplar | `ScriptStoryboard` | Schema, objective coverage, bounded length, supported claims |
| Content review | Script, example state trace, approved facts | Structured issues and proposed corrections | Deterministic checks plus human review for demo; model review alone is insufficient |
| Timed implementation | Frozen script, actual audio timing, cues, template docs | Template data or `ScenePackage` | Valid entry points/imports, unchanged narration, referenced assets exist |
| Preview repair | Specific errors, affected scenes, bounded frame samples | Targeted new scene revision | Re-run failed checks and invalidate downstream previews |

Estimated script word count is only a planning aid. Start around 90–120 spoken words for a 45-second example and measure actual speech. Do not shorten pronunciation or accelerate playback until speech is unintelligible to satisfy a duration check.

### 6.4 Controlled tools

These are proposed internal tool interfaces; none are implemented yet.

| Tool | Allowed behavior |
|---|---|
| `read_template_doc(doc_id)` | Read allowlisted immutable documentation, not arbitrary paths |
| `read_job_artifact(artifact_id)` | Read current job's approved JSON/text artifacts with output limits |
| `write_scene_file(relative_name, content)` | Write bounded UTF-8 source only under the current job's generated-scene directory |
| `validate_scene_package()` | Ask the sandbox broker to compile/typecheck with immutable configuration |
| `render_preview(scene_ids, frame_indices)` | Render bounded previews in the sandbox; controller validates scene/frame ranges |
| `inspect_preview(preview_id)` | Return selected images and sanitized measurements from this job |
| `submit_stage_result(payload)` | Validate structured output against the stage schema |

No general-purpose Bash, arbitrary filesystem read, HTTP client, package manager, credential read, or publication tool is exposed to the model. The controller calls ElevenLabs and storage itself. If an SDK integration cannot enforce this tool surface, do not grant broad execution to make it work; use a constrained tool loop or resolve the harness limitation.

### 6.5 Repair and budget policy

Proposed starting budgets: at most two content/schema repair rounds, two narration-duration revisions, and two scene-repair rounds per job; at most 24 agent turns across stages and a 20-minute overall wall-clock deadline. These values are tunable settings, not performance claims. Persist counters across worker restarts and retries. Provider transport retries do not grant fresh semantic-repair budgets.

Classify failures before retrying. Invalid scene imports, clipping, or wrong animation timing go to scene repair. Wrong spoken content returns to script approval and invalidates speech/timing. A missing voice or missing approved background is a dependency failure, not a reason to repeatedly ask Claude to rewrite code. Budget exhaustion yields an inspectable failure with the last valid artifacts retained.

Never declare a repair successful solely because Claude says it is fixed. Re-run actual validation/rendering. Known-template fallback is allowed only when its instructional content can express the brief correctly; record fallback usage, and do not count it as proof that custom scene generation succeeded.

## 7. ElevenLabs narration and captions

### 7.1 Voice configuration and requests

Configure `peter`, `stewie`, and `narrator` roles independently of the templates. The worker resolves role → provider voice ID, model, settings, pronunciation policy, and voice-config version. Exact character voices are unresolved; audition actual samples and check account/API availability before demo signoff. Do not silently substitute a voice while reporting an exact character match.

The timed text-to-speech endpoint returns audio and character-level timing, including raw and normalized alignment structures [S2]. Our adapter translates provider responses to internal audio/timing records; templates never consume provider-specific responses directly.

Generate one complete speaker turn or coherent narration beat per request, not one request per word. Process dialogue in storyboard order for assembly, even if a small bounded number of independent synthesis requests execute concurrently. Use the exact frozen spoken text. Pronounce code in understandable language; preserve code notation in visual overlays and explicit display-text mappings.

### 7.2 Audio cache and validation

Cache identity includes effective scope/owner, spoken-text hash, voice ID/config version, model, settings, pronunciation configuration, and requested format. Identical text spoken by different characters is not the same cache entry. Private audio must not be shared across owners.

Validate successful responses before caching: decode audio, probe actual duration, verify nonempty speech, enforce response-size limits, and validate alignment arrays. Each character must have matching start/end entries; values must be finite, nonnegative, ordered, and inside decoded duration within an explicit codec tolerance. Allow punctuation/space zero-length entries where appropriate. Reject mismatched or missing alignment rather than invent word times.

Preserve the original response alignment as a private diagnostic artifact. Choose raw or normalized alignment consistently with the text actually spoken. If provider normalization expands numbers or symbols, build an explicit normalized-to-display span mapping. Do not zip original characters to normalized timestamps by index. When mapping cannot be established, regenerate with explicit spoken wording or mark the segment for review; forced alignment would be a separately validated fallback, not an assumed service.

### 7.3 Assemble the authoritative timeline

Convert decoded segments to a common internal sample rate, proposed 48 kHz, and assemble in sample units before rounding for display. Codec padding must not accumulate between turns; verify decoded segment boundaries. Proposed turn pauses are 120–250 ms, stored explicitly. Avoid overlapping speakers in v1.

For segment i, its global offset is the sum of preceding decoded segment lengths and explicit pauses. A word's global start/end is its segment offset plus local alignment. Convert seconds to integer milliseconds once at the internal boundary; preserve sample offsets for exact audio assembly. Never repeatedly round elapsed durations from each prior segment.

Caption and cue intervals use half-open ranges `[start_ms, end_ms)`. A video frame at time `frame * 1000 / fps` displays the active caption for that time. The final frame count is `ceil(total_duration_ms * fps / 1000)` with only the minimal trailing silence required for frame alignment. Final measured export, including padding, must remain within 30–60 seconds; keep planning margin below 60 seconds.

### 7.4 Caption construction

1. Tokenize the aligned spoken text into display words, preserving punctuation and explicit pronunciation mappings.
2. Map each word to its first/last spoken character timing, then apply the segment offset.
3. Group into short readable phrases, initially about 3–7 words, capped by measured rendered width and two lines.
4. Never combine two speakers into one caption group. Break at speaker turns and meaningful pauses.
5. Render the active word highlight from authoritative timing. Store speaker, text spans, and timestamps in `captions.json`.
6. Export a WebVTT phrase track plus burned-in captions. Word timing remains available in JSON even if the player only supports phrase captions.

User-facing captions must not include model delivery tags. Visual-explainer captions occupy a dedicated configurable band, normally below the main diagram but above app controls. Dialogue captions remain in the middle as requested.

Proposed QC target: no cumulative caption drift; sampled words and semantic animation cues within 150 ms of their corresponding audible event during manual review. Numeric timestamp validity alone does not prove perceived synchronization. Check beginning, middle, end, and every speaker transition.

### 7.5 Duration and loudness

If speech is too long, revise the script to remove redundancy or narrow the objective, then regenerate changed segments and rebuild timing. If too short, add useful explanation or a follow-up; do not pad with long empty gameplay. Duration repair must retain all required teaching points.

Mute gameplay audio initially. Normalize final narration to a proposed -16 LUFS integrated target, with true peak at or below -1 dBTP, and verify levels empirically. Avoid a volume jump between Peter and Stewie. Optional effects are deferred until narration is clear. Loudness processing must preserve timing; any trim/time-stretch invalidates affected alignment.

## 8. Rendering and generated-code isolation

### 8.1 RenderJob and result

Preserve the existing internal `RenderJob` fields: `job_id`, `schema_version`, `generation_key`, `template_id`, `template_version`, `scene_data_ref`, `optional_scene_code_ref`, `audio_assets`, `alignment_ref`, `caption_data_ref`, `local_asset_manifest`, `output_spec`, and `timeout_seconds`.

The trusted controller resolves references to a fresh job workspace before execution. Manifest entries include logical asset ID, normalized relative path, SHA-256, media kind, size, and applicable dimensions/duration. Reject absolute paths, `..`, symlink escapes, unexpected file types, and digest mismatches. No arbitrary remote URL is accepted by the render interface.

`RenderResult` contains job ID, state, output references/hashes, measured duration, frame-check references, and bounded sanitized diagnostics. The result is untrusted until the controller validates containment, file type, size, checksum, and expected media structure. A renderer cannot change scope or mark a catalog entry ready.

### 8.2 Execution sequence

1. Stage the approved source package, pinned templates, audio, captions, images, fonts, and gameplay range.
2. Validate manifests, schemas, entry points, and allowlisted imports without executing generated code on the host.
3. Start the sandbox and compile/bundle there. Composition discovery also stays inside it.
4. Use Remotion still rendering for representative frame previews [S4]. Sample each scene, important state-change boundaries, caption changes, and speaker transitions.
5. Render a low-resolution preview with sound to inspect motion and timing that still frames cannot demonstrate.
6. Pass structured failures and selected frames to the agent for bounded repair if needed.
7. Render the final composition using Remotion's programmatic media renderer [S3].
8. Probe the output independently; produce thumbnail, captions, measurements, and final hashes.

The preview and final output use identical scene logic, audio, timing, fonts, and props; only render scale/encoding differ. A preview approval does not exempt final output from validation.

### 8.3 Sandbox requirements

Use a disposable container or equivalently isolated runtime per job on the renderer host. On a Mac, this requires a working container/VM backend; availability must be checked. A normal child process on the developer laptop is not accepted as isolation for model-generated code.

Required controls:

- Non-root user, read-only base filesystem, dropped capabilities, no-new-privileges, and a restrictive runtime profile.
- No host home/repository/secrets mounts, no Docker socket, and no cloud metadata access.
- Only read-only job inputs plus bounded temporary/output directories; never mount the entire application workspace.
- No external network egress or DNS. Remotion's local asset server may communicate only within the sandbox's own loopback/network namespace.
- Dependencies, compiler/bundler configuration, Chromium, fonts, and codecs preinstalled in the image. No runtime package installation.
- Whole process-tree termination on timeout/cancellation, with CPU/memory/process/disk limits and capped logs.

Proposed initial limits: 2 vCPU, 4 GiB RAM, 128 processes, 2 GiB scratch output, 10 MiB logs, 60 seconds compile, 120 seconds preview, and 300 seconds final render. Benchmark these on the demo host and tune explicitly; these are safeguards, not measured capacity. Preflight checks reject input packs that exceed staging/storage budgets.

Generated files may import only approved React/Remotion APIs and template helpers. Block Node process/filesystem/network modules, dynamic remote imports, eval-style execution, and arbitrary asset URLs. Import/static checks are additional filters; the sandbox remains mandatory because static checks are incomplete.

### 8.4 Final output profile

| Output | Proposed specification |
|---|---|
| Video | MP4 container, H.264, yuv420p, 1080 × 1920, 30 fps |
| Audio | AAC, 48 kHz, consistent channel layout |
| Start behavior | MP4 metadata positioned for progressive playback |
| Captions | Burned-in, plus WebVTT and word-timing JSON |
| Thumbnail | Representative JPEG/WebP frame without app UI |
| Duration | Measured 30–60 seconds, no clipped final word |
| Metadata | Exact recipe versions, artifact digests, dimensions, duration, QC status |

Codec/container choices are compatibility targets. Validate the actual result on the demo iPhone, including audio, aspect ratio, seeking, and background/resume behavior through Adi's player. Desktop playback is insufficient.

## 9. Jobs, persistence, and publication

### 9.1 Service interfaces and API behavior

Proposed internal functions:

| Function | Behavior |
|---|---|
| `request_generation(actor, lesson_request_id, format_id)` | Authorize, resolve brief, reuse or atomically enqueue; return video/job reference |
| `get_generation_status(actor, job_id)` | Owner-authorized stage/progress and sanitized errors |
| `retry_generation(actor, job_id)` | Authorize and classify retry; retain valid checkpoints and budgets |
| `cancel_generation(actor, job_id)` | Stop future claims, signal running render, prevent later publication |
| `publish_validated_variant(job_id, lease_token, result_ref)` | Trusted-worker-only conditional publication |

These names describe interfaces to implement, not new public endpoints. Existing read/playback routes remain as defined in the learning contract. If a demo needs a generation HTTP trigger, add a separate authenticated development route, disabled in normal client builds; return 202 and a job ID rather than holding the connection open. Final route names require a learning-contract update.

### 9.2 State mapping

| Internal work | Existing VideoVariant status |
|---|---|
| Brief assembled | `planned` |
| Waiting for worker/dependency slot | `queued` |
| Script/storyboard/content review | `scripting` |
| Speech synthesis and timeline assembly | `voicing` |
| Timed scene implementation, compile, preview, export | `rendering` |
| Final QC, human review, upload verification | `validating` |
| Committed ready assets | `ready` |
| Terminal failure | `failed` |

Use a separate internal `stage` and artifact revision to describe progress; do not add undocumented values to public status enums. A repair may return to an earlier stage. Global progress is descriptive, not an invented percentage of model completion. Cancellation uses the job contract's explicit cancellation state; non-ready videos never become feed-eligible.

Workers claim durable jobs with leases and periodic heartbeat. Use a monotonically increasing claim/fencing token or equivalent conditional writes so an expired worker cannot publish after another worker has reclaimed the job. Persist stage checkpoints before acknowledging completion. Cancellation and publication race through an authoritative conditional database transaction.

Guarantee one logical job and one authoritative publication, not exactly-once provider billing. If the worker dies after a provider call succeeds but before its result is durably saved, a retry may repeat that call unless the provider offers a verified idempotency mechanism. Record such ambiguity and preserve any recoverable artifact; do not invent provider guarantees.

### 9.3 Upload and visibility

Object storage uploads and database commits are not one atomic transaction. Use staged, nonpublic, immutable object keys; validate uploaded objects first; then commit ready metadata and `learning.video.ready` outbox event in one database transaction. A crash before commit leaves an orphan for cleanup, not a feed-visible partial video.

Publish only after required MP4, caption assets, thumbnail, and quality report exist. Shared publication requires an approved generic lineage and output review; private is the default. Keep prompt traces, source references, internal origin mappings, and voice/source approval evidence out of public manifests. Use short-lived playback URLs for private content and refresh them by stable asset ID.

A profile superseded before publication must not acquire a new binding to the obsolete plan. A generic output may still be retained as a catalog candidate if independently valid; it cannot silently attach to the current profile. Disconnect/deletion cancels pending private work and revokes private playback according to the owning domain's lifecycle policy.

## 10. Failure behavior

| Failure | Required handling |
|---|---|
| Unauthorized/missing private source | Fail before provider access; inaccessible resource response must not reveal another user's content |
| Insufficient support for objective | Mark needs-review internally; do not invent a source-backed explanation |
| Claude invalid output | Return precise schema/content errors within persisted repair budget |
| Claude/ElevenLabs throttling or transient outage | Bounded exponential backoff with jitter; honor provider retry hints; preserve checkpoints |
| Invalid credentials or inaccessible voice | Dependency/configuration error; no automatic repeated synthesis loop |
| Missing/bad character alignment | Regenerate or review segment; do not fabricate successful sync |
| Speech outside duration range | Revise script, revoice changed segments, invalidate timing-dependent output |
| No suitable gameplay interval | Try approved inventory; otherwise block on assets |
| Compile or animation error | Sandbox diagnostics and targeted repair; stop at budget |
| Sandbox limit exceeded | Kill process tree, record limit category; retry only with explicit valid policy |
| Upload interrupted | Resume/retry upload of existing validated assets; do not regenerate narration |
| Worker restart | Resume valid checkpoint after lease claim; reject stale worker writes |
| Human review rejects lesson | Keep not-ready; record content/visual issue and invalidate approval on repair |
| Any generation failure | Entertainment and already-ready lessons continue normally |

Error records use safe codes, retryability, stage, and correlation IDs. Never return provider keys, raw private prompts, local host paths, or full stack traces to the mobile client.

## 11. Configuration, observability, and local development

### 11.1 Configuration ownership

| Setting family | Location / purpose |
|---|---|
| `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` | Trusted generation worker; model auth/config |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_MODEL` | Trusted narration adapter |
| `ELEVENLABS_PETER_VOICE_ID`, `ELEVENLABS_STEWIE_VOICE_ID`, `ELEVENLABS_NARRATOR_VOICE_ID` | Role mapping; validate at preflight |
| Database and object-storage settings | Trusted API/worker only, using shared project conventions |
| Recipe/template/voice-config versions | Versioned server configuration |
| Job limits and repair budgets | Worker configuration; bounded per job |
| Renderer image digest and resource settings | Controller/runtime; not supplied by Claude |
| Approved background/character manifest | Asset catalog; only staged file refs go to renderer |

Provide placeholder `.env.example` files when implementation begins. No provider or service-role key enters mobile publishable configuration or renderer environment. Exact package versions, installation commands, and executable entry points are implementation deliverables; none are claimed to exist yet.

### 11.2 Metrics and diagnostics

Record job/stage latency, queue wait, model usage, synthesis characters, cache hit/miss, render time, resource-limit hits, repair counts, failure category, measured duration, and human approval outcome. Use job IDs and content hashes in routine logs rather than full prompts or narration. Store sensitive debugging artifacts privately with explicit retention; proposed failed-workspace retention is 24 hours, configurable for local debugging.

Track provider request IDs where available and label live, fixture, cached, placeholder, and fallback modes separately. A completed cached video must not be presented as a freshly generated live result. Generation latency and cost have no numeric SLA until measured; a few high-quality demos take priority over optimization.

### 11.3 Fake adapters

Implement local fakes before requiring teammate/provider integration:

- Academic resolver returns generic synthetic objectives and authorized private examples, including another owner's inaccessible source.
- Claude adapter returns deterministic valid/invalid storyboards and scene packages.
- Narration fake supplies synthetic timing and clearly labeled non-provider test audio; it cannot validate character voice quality.
- Render/storage fakes exercise job publication, missing assets, and failure handling.

Run at least one real provider path and one real isolated render separately. Passing fake-adapter tests establishes orchestration behavior only.

## 12. Verification and acceptance

### 12.1 Behavioral test matrix

| ID | Scenario | Passing evidence |
|---|---|---|
| V01 | Duplicate simultaneous requests | One authoritative job/variant; callers receive same logical reference |
| V02 | Private cross-user access/reuse | Source, status, intermediate assets, and playback inaccessible to other owner |
| V03 | Generic reuse | Reviewed generic video reused without copying private course metadata |
| V04 | Worker restart/lease expiration | Valid checkpoint resumes; stale worker cannot publish |
| V05 | Source prompt injection | Embedded instructions cannot grant tools, read other files, change scope, or bypass output checks |
| V06 | Incorrect linked-list trace | Validator/reviewer rejects overwritten successor or wrong final head |
| V07 | Normalized speech alignment | Numbers/code pronunciation map to captions without index drift |
| V08 | Multiple dialogue turns | Speaker changes, audio offsets, captions, and mouth states remain synchronized |
| V09 | Script or voice edit | Affected audio and downstream timing/render approvals invalidate correctly |
| V10 | Visual-only edit | Existing valid audio reused; visual QC reruns |
| V11 | Varied gameplay | Stored selections vary across approved maps/segments; retry reproduces same selection |
| V12 | Duration edge cases | Short/long narration repaired or rejected; final measured output stays 30–60 s |
| V13 | Generated-code escape attempts | Network/metadata, path traversal, host file, subprocess/resource-abuse attempts fail within sandbox controls |
| V14 | Preview/final render | Inspect frames and motion; no unreadable captions, missing characters, wrong arrows, or clipped words |
| V15 | Partial upload/cancellation | No ready metadata/event before complete assets; canceled/stale attempt cannot publish |
| V16 | Provider failure | Bounded retry and inspectable failure; no synchronous feed dependency |
| V17 | Two formats on iPhone | Both actual files play with intelligible audio, readable captions, correct framing, and stable player lifecycle |
| V18 | Publication scope | Private input cannot become shared through model output or renderer result |

Do not rely on snapshot tests that merely restate constants. Test malformed inputs, concurrency, ownership, timing transformations, and actual failure boundaries. Static import scans cannot satisfy V13 by themselves; verify runtime isolation.

### 12.2 Demo completion checklist

- One narrow objective has two independently reviewed 30–60 second videos with distinct teaching approaches where useful.
- Dialogue uses actual Minecraft parkour, bottom character placement, middle captions, and the question/correction dynamic.
- Exact requested voices are auditioned and approved, or the demo explicitly discloses voice placeholders; placeholder mode does not satisfy exact voice verification.
- At least two dialogue generations demonstrate different approved backgrounds; the intended larger asset inventory is tracked separately.
- Visual explainer contains meaningful custom animated state changes, not only text transitions.
- At least one live Claude generation, ElevenLabs synthesis, and isolated Remotion render is recorded with actual commands/config versions and results.
- Demonstrate duplicate reuse and a failed/retried stage without publishing a broken video.
- All demo lessons pass human content/visual review, and both formats play on the target iPhone.
- Precomputed approved videos are available for the presentation; live generation is demonstrated separately from uninterrupted feed playback.
- Update [Agastya's status](status/AGASTYA.md) and the [integration checklist](INTEGRATION.md) with evidence and remaining limits.

## 13. Implementation plan and separate-chat boundaries

The user may split implementation across chats after reviewing this plan. No parallel agents or implementation work are launched by this document.

| Phase | Deliverable | Depends on | Completion evidence |
|---|---|---|---|
| P0 | Runtime schemas, synthetic brief/storyboards, proposed interface signoff | Existing contracts | Shared fixtures validate; missing academic fields documented |
| P1 | Renderer runtime and manually authored versions of both templates | P0 and approved/test assets | Two inspected local renders with fake or recorded narration clearly labeled |
| P2 | ElevenLabs adapter, role config, alignment/captions | P0 | Real narration and measured caption/turn synchronization |
| P3 | Claude scripts and timed scene generation/repair | P0, P1, P2 | New brief produces inspected output without manual scene editing |
| P4 | Durable jobs, cache/reuse, scope-aware publication | P0; may develop against fakes alongside P1–P3 | Restart/idempotency/ownership/publication checks pass |
| P5 | End-to-end demo and iPhone validation | P1–P4 | Actual provider/device evidence and prepared fallback assets |

Proposed directory ownership if splitting Agastya's work:

| Chat/workstream | Sole editing scope | Handoff |
|---|---|---|
| Integrator/contracts/jobs | `contracts/schemas/learning`, video domain root/service/repository, API core/jobs, Python manifest, migration assembly, `fixtures/learning` | Frozen schemas and job/tool interfaces |
| Renderer/boilerplates | `services/renderer` and renderer-local tests/docs | Validate/preview/render entry points and immutable template versions |
| Claude generation | Proposed `services/api/app/modules/videos/generation` | Brief → storyboard and timed scene-package adapter |
| Narration/captions | Proposed `services/api/app/modules/videos/narration` | Segments → audio, normalized alignment, captions, cue-resolution inputs |

These subdirectories are proposed, not present implementations. Each implementation chat uses a separate worktree and records its handoff without editing other streams' files. The integrator alone updates shared Python dependencies, top-level video service assembly, schemas, and `docs/status/AGASTYA.md`. Request renderer JS package/workspace-lock changes through Adi, who owns the root JS workspace. Fixtures and schema changes flow through the integrator to avoid competing definitions.

### 13.1 Immediate unresolved inputs

| Input | Can work begin without it? | Resolution before completion |
|---|---|---|
| Claude and ElevenLabs credentials/model selection | Yes, with fakes | Real API preflight and generation run |
| Peter/Stewie voice IDs | Yes, with labeled placeholders | Audition and validate actual API voices |
| Character art/expression pack | Yes, with synthetic placeholders | Approved final art and renderer inspection |
| Varied Minecraft recordings | Yes, with synthetic test background | Acquire, catalog, inspect, and stage approved footage |
| Visual-reference videos | Yes | Use to refine pacing and style if supplied |
| Academic canonical-objective lookup | Yes, with synthetic adapter | Coordinate with Amogh; retain existing academic field semantics |
| Mobile overlay bounds | Yes, configurable defaults | Confirm with Adi and verify on iPhone |
| Container/VM runtime and capacity | Renderer scaffolding only | Verify actual isolation before executing generated code |

## 14. Proposed decisions and integration impact

See [decision 001](decisions/001-video-generation-pipeline.md) for the implementation proposal. This document does not rename any academic/feed/learning contract field or change public route semantics. New internal schemas are owned by Agastya. Public projections, new development endpoints, or additional required academic fields must be coordinated and versioned before implementation.

## 15. Primary references and evidence limits

Documentation checked November 13, 2026, America/New_York. These references support provider capabilities only; all pipeline orchestration, budgets, layouts, schemas, and acceptance thresholds above are project proposals. No reference proves this project's integration or device playback works.

- [S1: Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview): Python/TypeScript agent harness, tools, and API-key integration guidance.
- [S2: ElevenLabs speech with timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps): audio response and character-level raw/normalized alignment.
- [S3: Remotion renderMedia](https://www.remotion.dev/docs/renderer/render-media): programmatic media rendering from a composition and input props.
- [S4: Remotion renderStill](https://www.remotion.dev/docs/renderer/render-still): frame preview rendering.
- [Existing project references](REFERENCES.md): broader architecture background and verification limits.
