"""Local inspection artifacts, not a model score or an automatic visual approval."""

import json
import re
from pathlib import Path

from .media import atomic_json, run, sha256
from .models import digest


def inspection_windows(lesson):
    duration = lesson.get("frame_count", lesson.get("frames")) / 30
    candidates = [("opening", 0.0, min(2.5, duration))]
    shots = lesson.get("shots") or lesson.get("segments", [])
    if len(shots) > 48:
        raise ValueError("Motion review exceeds bounded shot count")
    for index in sorted({1, len(shots) // 2}):
        if 0 <= index < len(shots):
            boundary = shots[index]["start"]
            candidates.append(("transition", max(0, boundary - 0.7), min(duration, boundary + 1.8)))
    if shots:
        longest = max(shots, key=lambda shot: shot["end"] - shot["start"])
        center = (longest["start"] + longest["end"]) / 2
        candidates.append(("longest_shot", max(0, center - 2.5), min(duration, center + 2.5)))
        reuse = next((shot for shot in shots if shot.get("space_mode") == "enzyme_reuse"), None)
        if reuse:
            candidates.append(
                ("reaction_cycles", reuse["start"], min(reuse["end"], reuse["start"] + 5))
            )
    math = lesson.get("math", {})
    if math.get("kind") == "pythagorean_rearrangement":
        stage = next(stage for stage in math["stages"] if stage["kind"] == "rearrange")
        candidates.append(("area_rearrangement", stage["start"], stage["end"]))
    elif math.get("cells"):
        cell = math["cells"][0]
        candidates.append(("first_dot_product", cell["start"], min(cell["end"], cell["start"] + 5)))
    # Preserve specialized labels when a whole-action interval is identical.
    for index, shot in enumerate(shots):
        candidates.append((f"shot_{index:02d}_complete_action", shot["start"], shot["end"]))
    candidates.append(("payoff", max(0, duration - 2.5), duration))
    unique = {}
    for purpose, start, end in candidates:
        if not 0 <= start < end <= duration:
            raise ValueError("Invalid motion inspection interval")
        unique.setdefault((round(start, 3), round(end, 3)), purpose)
    return [
        dict(purpose=purpose, start=start, end=end) for (start, end), purpose in unique.items()
    ]


def stage_motion_review(work: Path, lesson: dict):
    source = work / "output/lesson.mp4"
    folder = work / "output/motion-review"
    windows = inspection_windows(lesson)
    key = digest({"version": 2, "video_sha256": sha256(source), "windows": windows})
    index_path = folder / "index.json"
    if index_path.exists():
        cached = json.loads(index_path.read_text())
        if (
            cached.get("key") == key
            and isinstance(cached.get("clips"), list)
            and len(cached["clips"]) == len(windows)
            and all(
                re.fullmatch(r"motion-[0-9]{2}\.mp4", item["file"])
                and item["strip"] == item["file"].replace(".mp4", ".jpg")
                and not (folder / item["file"]).is_symlink()
                and not (folder / item["strip"]).is_symlink()
                and (folder / item["file"]).is_file()
                and sha256(folder / item["file"]) == item["sha256"]
                and (folder / item["strip"]).is_file()
                and sha256(folder / item["strip"]) == item["strip_sha256"]
                for item in cached["clips"]
            )
        ):
            return cached
    folder.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, window in enumerate(windows):
        clip, strip = folder / f"motion-{i:02}.mp4", folder / f"motion-{i:02}.jpg"
        length = window["end"] - window["start"]
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                str(window["start"]),
                "-i",
                source,
                "-t",
                str(length),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                "scale=540:960",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "26",
                "-threads",
                "2",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                clip,
            ],
            timeout=60,
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                clip,
                "-vf",
                f"fps={6 / length},scale=180:320,tile=6x1:nb_frames=6",
                "-frames:v",
                "1",
                strip,
            ],
            timeout=30,
        )
        clips.append(
            {
                **window,
                "file": clip.name,
                "strip": strip.name,
                "sha256": sha256(clip),
                "strip_sha256": sha256(strip),
            }
        )
    result = {
        "schema_version": "1",
        "key": key,
        "source_video_sha256": sha256(source),
        "status": "inspection_artifacts_only",
        "paid_model_calls": 0,
        "clips": clips,
    }
    atomic_json(index_path, result)
    (folder / "README.txt").write_text(
        "Play these clips with audio to inspect timing, entrances, exits and transitions.\n"
        "Each JPG shows six chronological frames from its clip.\n"
        "For EACH action inspect: target-facing body and eyeline; hand/prop contact;\n"
        "foot support and path; anticipation, contact, follow-through and settle;\n"
        "object identity/count continuity; camera occlusion and caption-safe framing.\n"
        "Inspect transitions and the complete exported video as well.\n"
        "These files are inspection aids, not proof of natural delivery or engagement.\n"
        "A strip cannot establish smooth motion; see the source MP4 for the complete lesson.\n"
    )
    return result
