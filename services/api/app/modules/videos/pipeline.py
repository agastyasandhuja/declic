import json
import math
import os
import random
import shutil
import time
import wave
from pathlib import Path

from .engagement import POLICY_VERSION, pause_after, timed_teaching_beats, timing_issues
from .generation.providers import (
    REFERENCE_SYSTEM,
    STORYBOARD_SYSTEM,
    Claude,
    ElevenLabs,
    ProviderError,
)
from .images import stage_images
from .media import atomic_json, probe, run, sha256
from .models import Brief, Storyboard, digest
from .narration.service import synthesize
from .narration.timing import alignment_words, caption_groups, resolve_cue, vtt
from .rendering import render
from .trace import linked_list_trace

ROOT = Path(__file__).resolve().parents[5]
TEMPLATES = ROOT / "services/renderer/templates"


def generation_recipe(*, fixture=False, custom_scene=False):
    background_mode = os.getenv("VIDEO_BACKGROUND_MODE", "auto")
    if background_mode not in {"auto", "concept_only", "gameplay"}:
        raise ValueError("VIDEO_BACKGROUND_MODE must be auto, concept_only or gameplay")
    return {
        "fixture": fixture,
        "claude": "fixture" if fixture else os.getenv("VIDEO_CLAUDE_MODEL", "claude-sonnet-4-5"),
        "tts": "macos-say" if fixture else os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
        "voices": (
            {"peter": "Alex", "stewie": "Daniel", "narrator": "Samantha"}
            if fixture
            else {
                role: os.getenv(f"ELEVENLABS_{role.upper()}_VOICE_ID", "")
                for role in ("peter", "stewie", "narrator")
            }
        ),
        "custom_scene": custom_scene,
        "voice_revisions": {}
        if fixture
        else {
            role: os.getenv(f"ELEVENLABS_{role.upper()}_VOICE_REVISION", "")
            for role in ("peter", "stewie", "narrator")
            if os.getenv(f"ELEVENLABS_{role.upper()}_VOICE_REVISION")
        },
        "engagement_policy": POLICY_VERSION,
        "timing_source": digest(
            {
                name: sha256(Path(__file__).parent / name)
                for name in (
                    "engagement.py",
                    "narration/timing.py",
                    "narration/service.py",
                    "pipeline.py",
                    "images.py",
                    "music.py",
                    "math_video.py",
                    "motion_review.py",
                    "models.py",
                    "generation/providers.py",
                )
            }
        ),
        "background_mode": background_mode,
        "system_prompt": digest([STORYBOARD_SYSTEM, REFERENCE_SYSTEM]),
        "template": "4.1.0",
        "source_assets": {
            name: sha256(ROOT / ".local/video-assets" / name)
            for name in ("parkour.mp4", "peter.png", "stewie.png", "stewie-standing-v2.png")
            if (ROOT / ".local/video-assets" / name).is_file()
        },
        "scene_api": "trusted-trace-2" if custom_scene else "authored-trace-1",
        "renderer_image": os.getenv(
            "VIDEO_RENDER_IMAGE", "hackumass-renderer:reference-v9-semantic"
        ),
        "renderer_source": digest(
            {
                name: sha256(ROOT / "services/renderer" / name)
                for name in (
                    "src/Root.tsx",
                    "src/ReferenceLesson.tsx",
                    "src/SemanticDiagram.tsx",
                    "src/PopCaptions.tsx",
                    "src/SpaceScene.tsx",
                    "src/SpaceScenesV3.tsx",
                    "src/MathLesson.tsx",
                    "src/PythagoreanLesson.tsx",
                    "src/BiologyScenes.tsx",
                    "src/PaymentScenes.tsx",
                    "src/DecisionScenes.tsx",
                    "render.mjs",
                    "validate.mjs",
                    "package-lock.json",
                )
            }
        ),
        "prompts": {
            name: sha256(TEMPLATES / name)
            for name in (
                "dialogue_gameplay/prompt.txt",
                "visual_explainer/prompt.txt",
                "visual_explainer/scene-api.txt",
                "dialogue_gameplay/reference-prompt.txt",
                "visual_explainer/reference-prompt.txt",
                "space_explainer/reference-prompt.txt",
                "space_explainer/prompt.txt",
            )
        },
        "voice_disclosure": "Local fixture voices"
        if fixture
        else os.getenv("VIDEO_VOICE_DISCLOSURE", "AI voices"),
    }


def artifact_digests(work):
    paths = [
        "output/lesson.mp4",
        "captions.vtt",
        "captions.json",
        "output/frame-01.png",
        "output/quality.json",
    ]
    if (work / "output/CREDITS.txt").is_file():
        paths.append("output/CREDITS.txt")
    return {name: sha256(work / name) for name in paths}


def generate(
    brief: Brief,
    work: Path,
    *,
    fixture=False,
    custom_scene=False,
    preview=False,
    render_video=True,
    stage=lambda _: None,
    check_cancelled=lambda: None,
    deadline=None,
    scene_feedback=None,
    storyboard_feedback=None,
    storyboard_override=None,
    _frozen_recipe=None,
):
    if brief.format_id == "math_explainer":
        from .math_video import generate_math

        return generate_math(
            brief,
            work,
            fixture=fixture,
            preview=preview,
            render_video=render_video,
            stage=stage,
            check_cancelled=check_cancelled,
        )
    deadline = deadline or time.monotonic() + (
        1800 if brief.format_id == "space_explainer" else 1200
    )

    def checkpoint():
        check_cancelled()
        if time.monotonic() >= deadline:
            raise ProviderError("GENERATION_DEADLINE_EXCEEDED")

    checkpoint()
    work.mkdir(parents=True, exist_ok=True)
    stage("scripting")
    budget_path = work / "budgets.json"
    budget = (
        json.loads(budget_path.read_text())
        if budget_path.exists()
        else {"turns": 0, "duration_repairs": 0, "scene_repairs": 0}
    )

    def charge():
        checkpoint()
        if budget["turns"] >= max(1, min(40, int(os.getenv("VIDEO_MAX_CLAUDE_CALLS", "6")))):
            raise ProviderError("AGENT_BUDGET_EXHAUSTED")
        budget["turns"] += 1
        atomic_json(budget_path, budget)

    claude = (
        None
        if fixture
        else Claude(
            cache_dir=work / "model-cache",
            charge=charge,
            diagnostic=lambda value: atomic_json(
                work / f"claude-validation-{budget['turns']:02d}.json", value
            ),
        )
    )
    eleven = None if fixture else ElevenLabs()
    voices = {
        role: os.environ.get(f"ELEVENLABS_{role.upper()}_VOICE_ID", "")
        for role in ("peter", "stewie", "narrator")
    }
    if fixture:
        voices = {"peter": "Alex", "stewie": "Daniel", "narrator": "Samantha"}
    required_roles = ["peter", "stewie"] if brief.format_id == "dialogue_gameplay" else ["narrator"]
    if any(not voices[role] for role in required_roles):
        raise ProviderError("MISSING_VOICE_CONFIGURATION")
    recipe = (
        dict(_frozen_recipe)
        if _frozen_recipe is not None
        else generation_recipe(fixture=fixture, custom_scene=custom_scene)
    )
    reference = brief.presentation in {"reference_v2", "reference_v3"}
    if reference and custom_scene:
        raise ValueError("Reference templates use authored scenes; custom_scene requires guided_v1")
    background_mode = recipe["background_mode"]
    if background_mode == "auto":
        background_mode = (
            "gameplay" if reference and brief.format_id == "dialogue_gameplay" else "concept_only"
        )
    prompt_name = "reference-prompt.txt" if reference else "prompt.txt"
    if storyboard_feedback and _frozen_recipe is None:
        recipe["editorial_feedback"] = digest(storyboard_feedback)
    key = brief.generation_key(recipe)
    atomic_json(
        work / "request.json",
        {"brief": brief.model_dump(), "recipe": recipe, "generation_key": key},
    )
    board_path = work / "storyboard.json"
    board_key = digest(
        {
            "brief": brief.teaching_payload(),
            "model": recipe["claude"],
            "prompt": recipe["prompts"][f"{brief.format_id}/{prompt_name}"],
            "system_prompt": recipe["system_prompt"],
            "engagement_policy": recipe["engagement_policy"],
            "editorial_feedback": None,
        }
    )
    if storyboard_override is not None:
        authored = Storyboard.model_validate(storyboard_override).validate_for(
            brief, require_engagement=True
        )
        atomic_json(board_path, authored.model_dump())
        atomic_json(work / "storyboard-key.json", board_key)
        atomic_json(
            work / "editorial-corrections.json",
            {
                "source": "explicit_local_storyboard",
                "storyboard_digest": digest(authored.model_dump()),
                "verification": "Live content/frame gates still required; not fixture mode.",
            },
        )
    if (
        not storyboard_feedback
        and board_path.exists()
        and json.loads((work / "storyboard-key.json").read_text()) == board_key
    ):
        board = Storyboard.model_validate_json(board_path.read_text()).validate_for(
            brief, require_engagement=True
        )
        if not fixture:
            review_path = work / "content-review.json"
            # Revalidate the exact brief/model/prompt as well as the script. The
            # provider cache avoids an HTTP call when ALL these inputs match.
            review = claude.review(brief, board)
            atomic_json(
                review_path,
                {
                    **review.model_dump(),
                    "storyboard_digest": digest(board.model_dump()),
                    "brief_digest": digest(brief.teaching_payload()),
                    "model": recipe["claude"],
                },
            )
            if not review.passed or review.issues:
                raise ProviderError("CONTENT_REVIEW_REQUIRED")

    else:
        if fixture:
            fixture_name = f"{brief.format_id}.json"
            if reference:
                prefix = "revised" if brief.presentation == "reference_v3" else "reference"
                fixture_name = f"{prefix}-{brief.format_id}.json"
                if (
                    brief.trace_kind == "linked_list_reverse"
                    and brief.format_id == "visual_explainer"
                ):
                    fixture_name = "reference-linked-list-visual_explainer.json"
            fixture_name = {
                "sunk-cost-future-choice": "new-sunk-cost-dialogue.json",
                "enzyme-competitive-inhibition": "revised-enzyme-animation.json",
                "installments-vs-price": "new-installments-animation.json",
            }.get(brief.objective_id, fixture_name)
            board = Storyboard.model_validate_json(
                (ROOT / "fixtures/learning" / fixture_name).read_text()
            ).validate_for(brief, require_engagement=True)
        else:
            board = claude.storyboard(brief, TEMPLATES, storyboard_feedback)
            for content_attempt in range(3):
                review = claude.review(brief, board)
                atomic_json(
                    work / "content-review.json",
                    {**review.model_dump(), "storyboard_digest": digest(board.model_dump())},
                )
                if review.passed and not review.issues:
                    break
                atomic_json(work / f"content-repair-{content_attempt}.json", review.model_dump())
                if content_attempt == 2:
                    raise ProviderError("CONTENT_REVIEW_REQUIRED")
                board = claude.storyboard(
                    brief,
                    TEMPLATES,
                    {
                        "previous": board.model_dump(),
                        "issues": review.issues,
                        "instruction": "Remove unsupported claims and repair every listed issue.",
                    },
                )
        atomic_json(board_path, board.model_dump())
        atomic_json(work / "storyboard-key.json", board_key)
    stage("voicing")
    pack = work / "pack"
    assets = pack / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    offset, words, segments, events, audio_paths = 0.0, [], [], [], []
    for i, segment in enumerate(board.segments):
        checkpoint()
        source, meta = synthesize(
            segment,
            brief,
            eleven,
            voices[segment.speaker_role],
            ROOT / ".local/video-audio-cache",
            fixture,
        )
        staged = assets / f"segment-{i}.wav"
        shutil.copyfile(source, staged)
        audio_paths.append(staged)
        segment_words = alignment_words(
            meta["alignment"], meta["duration"], offset, segment.speaker_role
        )
        for word in segment_words:
            word["segment_id"] = segment.segment_id
        words.extend(segment_words)
        for event in board.events:
            if event.cue.segment_id == segment.segment_id:
                events.append(
                    {
                        "time": resolve_cue(event.cue, segment, segment_words),
                        "action": event.action,
                        "node": event.node,
                    }
                )
        segments.append(
            {
                "id": segment.segment_id,
                "speaker": segment.speaker_role,
                "start": offset,
                "end": offset + meta["duration"],
                "envelope": meta["envelope"],
            }
        )
        offset += meta["duration"]
        pause = pause_after(board, segment.segment_id)
        if pause:
            # Real silence, not just a visual hold: every subsequent cue shares this offset.
            silence = assets / f"pause-{i}.wav"
            with wave.open(str(silence), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(48000)
                audio.writeframes(b"\x00\x00" * round(pause * 48000))
            audio_paths.append(silence)
            offset += pause
    # Reject cue reordering, including semantic events accidentally placed in earlier segments.
    expected = [(e.action, e.node) for e in board.events]
    events.sort(key=lambda e: e["time"])
    if [(e["action"], e["node"]) for e in events] != expected:
        raise ValueError("Audio cues contradict validated pointer trace")
    if any(a["time"] >= b["time"] for a, b in zip(events, events[1:], strict=False)):
        raise ValueError("Trace actions require distinct increasing speech cues")
    duration = math.ceil((offset + 0.3) * 30) / 30
    teaching_beats = timed_teaching_beats(board, segments)
    issues = timing_issues(teaching_beats) if not reference else []
    if reference and segments[0]["end"] > 6:
        issues.append("Shorten the opening to finish within six measured seconds")
    semantic = brief.installment_example or any(
        shot.space_mode.startswith("enzyme_") and shot.kind == "space" for shot in board.shots
    )
    if brief.format_id == "dialogue_gameplay" and any(
        s.motion_scene != "none" for s in board.shots
    ):
        semantic = True
    if semantic:
        issues.extend(
            f"Shorten {segment['id']} from {segment['end'] - segment['start']:.1f}s to at most 8s. "
            "Keep one idea per shot and remove duplicate qualifications."
            for segment in segments
            if segment["end"] - segment["start"] > 8
        )
    if not 30 <= duration <= 60 or issues:
        if not fixture and budget["duration_repairs"] < 2:
            budget["duration_repairs"] += 1
            atomic_json(budget_path, budget)
            revised = claude.storyboard(
                brief,
                TEMPLATES,
                {
                    "measured_duration": duration,
                    "timing_issues": issues,
                    "previous": board.model_dump(),
                    "instruction": (
                        "Revise speech length and opening timing; retain every fact and cue. "
                        "Never fix timing by speeding up speech. "
                        + (
                            "No teaching beats or pauses for reference_v2."
                            if reference
                            else "Retain teaching beats; the five seconds of pauses are included."
                        )
                    ),
                },
            )
            review = claude.review(brief, revised)
            if not review.passed or review.issues:
                raise ProviderError("CONTENT_REVIEW_REQUIRED")
            atomic_json(board_path, revised.model_dump())
            atomic_json(
                work / "content-review.json",
                {**review.model_dump(), "storyboard_digest": digest(revised.model_dump())},
            )
            return generate(
                brief,
                work,
                fixture=fixture,
                custom_scene=custom_scene,
                preview=preview,
                render_video=render_video,
                stage=stage,
                check_cancelled=check_cancelled,
                deadline=deadline,
                scene_feedback=scene_feedback,
                storyboard_feedback=storyboard_feedback,
                _frozen_recipe=recipe,
            )
        raise ValueError(
            f"NARRATION_DURATION_REVIEW: {duration:.2f} seconds; {issues}; revise script"
        )
    concat = work / "audio-inputs.txt"
    concat.write_text("".join(f"file 'pack/assets/{p.name}'\n" for p in audio_paths))
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "1",
            "-i",
            concat,
            "-af",
            "loudnorm=I=-16:TP=-1:LRA=11,apad",
            "-t",
            str(duration),
            "-ar",
            "48000",
            "-ac",
            "1",
            assets / "narration.wav",
        ]
    )
    captions = caption_groups(words)
    (work / "captions.vtt").write_text(vtt(captions))
    atomic_json(work / "captions.json", captions)
    characters, background = {}, None
    asset_dir = ROOT / ".local/video-assets"
    if brief.format_id == "dialogue_gameplay":
        for role in ("peter", "stewie"):
            character_source = asset_dir / f"{role}.png"
            if reference and role == "stewie" and (asset_dir / "stewie-standing-v2.png").is_file():
                character_source = asset_dir / "stewie-standing-v2.png"
            if character_source.is_file():
                shutil.copyfile(character_source, assets / f"{role}.png")
                characters[role] = f"{role}.png"
        background_file = asset_dir / "parkour.mp4"
        if background_mode == "gameplay" and background_file.is_file():
            bg_duration = float(probe(background_file)["format"]["duration"])
            if bg_duration < duration + 2:
                raise ValueError("Gameplay interval too short")
            selection_path = work / "background-selection.json"
            source_hash = sha256(background_file)
            if selection_path.exists():
                selection = json.loads(selection_path.read_text())
                if selection["source_sha256"] != source_hash:
                    raise ValueError("Gameplay changed; use a new recipe workspace")
                start = selection["start"]
            else:
                start = round(random.Random(key).uniform(5, max(5, bg_duration - duration - 5)), 3)
                atomic_json(
                    selection_path,
                    {
                        "source_sha256": source_hash,
                        "start": start,
                        "duration": duration,
                        "seed": key,
                        "source": "user_provided",
                        "review": "pending",
                    },
                )
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-ss",
                    str(start),
                    "-i",
                    background_file,
                    "-t",
                    str(duration),
                    "-an",
                    "-vf",
                    "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "22",
                    assets / "background.mp4",
                ],
                timeout=180,
            )
            background = "background.mp4"
    checkpoint()
    stage("sourcing_images")
    images = stage_images(brief, board, claude, work, assets, fixture=fixture)
    by_segment = {s["id"]: s for s in segments}
    shots = [
        {
            **s.model_dump(),
            "start": by_segment[s.segment_id]["start"],
            "end": by_segment[s.segment_id]["end"],
        }
        for s in board.shots
    ]
    if shots:
        shots[-1]["end"] = duration
    lesson = {
        "schema_version": "1",
        "format_id": brief.format_id,
        "title": board.title,
        "values": brief.input_values,
        "frame_count": round(duration * 30),
        "events": events,
        "trace": linked_list_trace(brief.input_values, events)
        if brief.trace_kind == "linked_list_reverse"
        else [],
        "trace_kind": brief.trace_kind,
        "presentation": brief.presentation,
        "visual_strategy": brief.visual_strategy,
        "shots": shots,
        "images": images,
        "installment_example": brief.installment_example.model_dump()
        if brief.installment_example
        else None,
        "captions": captions,
        "segments": segments,
        "teaching_beats": teaching_beats,
        "background_mode": background_mode,
        "characters": characters,
        "background": background,
        "custom_scene": custom_scene,
        "disclosure": "Local fixture voices · estimated captions"
        if fixture
        else recipe["voice_disclosure"],
    }
    if custom_scene:
        if fixture:
            raise ValueError("Custom scene generation requires live Claude")
        scene_key = digest(
            {"lesson": lesson, "api": sha256(TEMPLATES / "visual_explainer/scene-api.txt")}
        )
        if (
            not (pack / "scene.tsx").exists()
            or not (work / "scene-key.json").exists()
            or json.loads((work / "scene-key.json").read_text()) != scene_key
            or scene_feedback
        ):
            feedback = None
            if scene_feedback:
                if budget["scene_repairs"] >= 2:
                    raise ProviderError("SCENE_REPAIR_BUDGET_EXHAUSTED")
                budget["scene_repairs"] += 1
                atomic_json(budget_path, budget)
                feedback = {
                    "errors": scene_feedback[:6000],
                    "previous": (pack / "scene.tsx").read_text(),
                }
            scene = claude.scene(
                brief, lesson, (TEMPLATES / "visual_explainer/scene-api.txt").read_text(), feedback
            )
            (pack / "scene.tsx").write_text(scene.source)
            atomic_json(work / "scene-key.json", scene_key)
    atomic_json(pack / "lesson.json", lesson)
    files = [f for f in pack.rglob("*") if f.is_file() and f.name != "manifest.json"]
    atomic_json(
        pack / "manifest.json",
        {
            "schema_version": "1",
            "files": [
                {"path": str(f.relative_to(pack)), "sha256": sha256(f), "size": f.stat().st_size}
                for f in files
            ],
        },
    )
    if render_video and brief.presentation == "reference_v3" and not fixture:
        stage("reviewing_rendered_frames")
        render(pack, work / "preview-frames", True, check_cancelled=checkpoint, stills_only=True)
        review = claude.review_render(brief, lesson, work / "preview-frames")
        atomic_json(
            work / "render-review.json",
            {
                **review.model_dump(),
                "lesson_digest": digest(lesson),
                "renderer_source": recipe["renderer_source"],
                "frames_digest": digest(
                    {
                        i["file"]: sha256(work / "preview-frames" / i["file"])
                        for i in json.loads((work / "preview-frames/frame-index.json").read_text())
                    }
                ),
                "model": claude.model,
                "scope": "sampled_frames",
            },
        )
        atomic_json(work / "provider-usage.json", claude.usage)
        if not review.passed or review.issues:
            if review.repair_scope != "storyboard":
                # Authored geometry defects need an implementation repair. Rewording
                # speech cannot fix a moving label or a path intersection.
                raise ProviderError("SCENE_IMPLEMENTATION_REVIEW_REQUIRED")
            if budget["scene_repairs"] >= 2:
                raise ProviderError("RENDER_REVIEW_REQUIRED")
            budget["scene_repairs"] += 1
            atomic_json(budget_path, budget)
            return generate(
                brief,
                work,
                fixture=fixture,
                preview=preview,
                custom_scene=custom_scene,
                render_video=render_video,
                check_cancelled=check_cancelled,
                stage=stage,
                deadline=deadline,
                _frozen_recipe=recipe,
                storyboard_feedback=json.dumps(
                    {
                        "previous": board.model_dump(),
                        "render_issues": review.issues,
                        "instruction": (
                            "Repair timestamped defects with supported scenes and concise speech. "
                            "Preserve correct facts/lines. Avoid titles, sources and prose cards. "
                            "Labels cannot change renderer geometry; report unresolved defects."
                        ),
                    }
                ),
            )
    stage("rendering")
    while True:
        try:
            report = (
                render(pack, work / "output", preview, check_cancelled=checkpoint)
                if render_video
                else {"media_checks": "not_run"}
            )
            break
        except RuntimeError:
            if not custom_scene or budget["scene_repairs"] >= 2:
                raise
            budget["scene_repairs"] += 1
            atomic_json(budget_path, budget)
            diagnostic = work / "output/renderer.log"
            scene = claude.scene(
                brief,
                lesson,
                (TEMPLATES / "visual_explainer/scene-api.txt").read_text(),
                {
                    "errors": diagnostic.read_text()[-6000:]
                    if diagnostic.exists()
                    else "Render failed",
                    "previous": (pack / "scene.tsx").read_text(),
                },
            )
            (pack / "scene.tsx").write_text(scene.source)
            atomic_json(
                pack / "manifest.json",
                {
                    "schema_version": "1",
                    "files": [
                        {
                            "path": str(f.relative_to(pack)),
                            "sha256": sha256(f),
                            "size": f.stat().st_size,
                        }
                        for f in files
                    ],
                },
            )
    credits = [
        "AI-generated narration and authored schematic animation. Human aesthetic review pending."
    ]
    for image in images.values():
        credits.append(
            " | ".join(
                str(v)
                for v in (
                    image.get("creator", "Source"),
                    image.get("source_url", image.get("url", "")),
                    image.get("license", ""),
                    image.get("license_url", ""),
                )
            )
        )
    credit_text = "\n".join(credits) + "\n"
    (work / "CREDITS.txt").write_text(credit_text)
    if render_video:
        (work / "output/CREDITS.txt").write_text(credit_text)
    motion_inspection = None
    if render_video:
        from .motion_review import stage_motion_review

        stage("staging_motion_inspection")
        motion_inspection = stage_motion_review(work, lesson)
    stage("validating")
    checkpoint()
    manifest = {
        "schema_version": "1",
        "generation_key": key,
        "recipe": recipe,
        "scope": brief.scope,
        "owner_user_id": brief.owner_user_id,
        "status": "validating",
        "quality": report,
        "motion_inspection": motion_inspection,
        "teaching_checks": {
            "policy": "reference-cinematic-2" if reference else POLICY_VERSION,
            "structure": "passed",
            "measured_opening": "passed",
            "prediction_pause_seconds": 0 if reference else 2,
            "retrieval_pause_seconds": 0 if reference else 3,
            "engagement_uplift": "unmeasured",
            "learning_uplift": "unmeasured",
        },
        "storyboard_digest": digest(board.model_dump()),
        "image_credits": images,
        "editorial_corrections": json.loads((work / "editorial-corrections.json").read_text())
        if (work / "editorial-corrections.json").exists()
        else None,
        "provider_usage": getattr(claude, "usage", []),
        "fixture": fixture,
        "custom_scene": custom_scene,
        "human_review": "pending",
        "artifact_digests": artifact_digests(work) if render_video else {},
    }
    atomic_json(work / "generation-manifest.json", manifest)
    return manifest
