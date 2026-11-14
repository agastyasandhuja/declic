import json
import math
import os
import random
import shutil
import time
from pathlib import Path

from .generation.providers import Claude, ElevenLabs, ProviderError
from .media import atomic_json, probe, run, sha256
from .models import Brief, Storyboard, digest
from .narration.service import synthesize
from .narration.timing import alignment_words, caption_groups, resolve_cue, vtt
from .rendering import render
from .trace import linked_list_trace

ROOT = Path(__file__).resolve().parents[5]
TEMPLATES = ROOT / "services/renderer/templates"


def generation_recipe(*, fixture=False, custom_scene=False):
    return {
        "fixture": fixture,
        "claude": "fixture" if fixture else os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5"),
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
        "template": "1.0.0",
        "scene_api": "trusted-trace-2" if custom_scene else "authored-trace-1",
        "renderer_image": os.getenv("VIDEO_RENDER_IMAGE", "hackumass-renderer:0.1"),
        "renderer_source": digest(
            {
                name: sha256(ROOT / "services/renderer" / name)
                for name in ("src/Root.tsx", "render.mjs", "validate.mjs", "package-lock.json")
            }
        ),
        "prompts": {
            name: sha256(TEMPLATES / name)
            for name in (
                "dialogue_gameplay/prompt.txt",
                "visual_explainer/prompt.txt",
                "visual_explainer/scene-api.txt",
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
):
    deadline = deadline or time.monotonic() + 1200

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
        if budget["turns"] >= 24:
            raise ProviderError("AGENT_BUDGET_EXHAUSTED")
        budget["turns"] += 1
        atomic_json(budget_path, budget)

    claude = (
        None
        if fixture
        else Claude(
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
    required_roles = ["narrator"] if brief.format_id == "visual_explainer" else ["peter", "stewie"]
    if any(not voices[role] for role in required_roles):
        raise ProviderError("MISSING_VOICE_CONFIGURATION")
    recipe = generation_recipe(fixture=fixture, custom_scene=custom_scene)
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
            "prompt": recipe["prompts"][f"{brief.format_id}/prompt.txt"],
        }
    )
    if board_path.exists() and json.loads((work / "storyboard-key.json").read_text()) == board_key:
        board = Storyboard.model_validate_json(board_path.read_text()).validate_for(brief)
    else:
        if fixture:
            board = Storyboard.model_validate_json(
                (ROOT / f"fixtures/learning/{brief.format_id}.json").read_text()
            ).validate_for(brief)
        else:
            board = claude.storyboard(brief, TEMPLATES)
            review = claude.review(brief, board)
            atomic_json(work / "content-review.json", review.model_dump())
            if not review.passed or review.issues:
                raise ProviderError("CONTENT_REVIEW_REQUIRED")
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
    # Reject cue reordering, including semantic events accidentally placed in earlier segments.
    expected = [(e.action, e.node) for e in board.events]
    events.sort(key=lambda e: e["time"])
    if [(e["action"], e["node"]) for e in events] != expected:
        raise ValueError("Audio cues contradict validated pointer trace")
    if any(a["time"] >= b["time"] for a, b in zip(events, events[1:], strict=False)):
        raise ValueError("Trace actions require distinct increasing speech cues")
    duration = math.ceil((offset + 0.3) * 30) / 30
    if not 30 <= duration <= 60:
        if not fixture and budget["duration_repairs"] < 2:
            budget["duration_repairs"] += 1
            atomic_json(budget_path, budget)
            revised = claude.storyboard(
                brief,
                TEMPLATES,
                {
                    "measured_duration": duration,
                    "previous": board.model_dump(),
                    "instruction": "Revise duration; retain every fact and cue",
                },
            )
            review = claude.review(brief, revised)
            if not review.passed or review.issues:
                raise ProviderError("CONTENT_REVIEW_REQUIRED")
            atomic_json(board_path, revised.model_dump())
            atomic_json(work / "content-review.json", review.model_dump())
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
            )
        raise ValueError(
            f"NARRATION_DURATION_REVIEW: {duration:.2f} seconds; revise script, never speed it up"
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
            if (asset_dir / f"{role}.png").is_file():
                shutil.copyfile(asset_dir / f"{role}.png", assets / f"{role}.png")
                characters[role] = f"{role}.png"
        background_file = asset_dir / "parkour.mp4"
        if background_file.is_file():
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
    lesson = {
        "schema_version": "1",
        "format_id": brief.format_id,
        "title": board.title,
        "values": brief.input_values,
        "frame_count": round(duration * 30),
        "events": events,
        "trace": linked_list_trace(brief.input_values, events),
        "captions": captions,
        "segments": segments,
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
        "provider_usage": getattr(claude, "usage", []),
        "fixture": fixture,
        "custom_scene": custom_scene,
        "human_review": "pending",
        "artifact_digests": artifact_digests(work) if render_video else {},
    }
    atomic_json(work / "generation-manifest.json", manifest)
    return manifest
