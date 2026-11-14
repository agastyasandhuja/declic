"""Only this broker may execute generated scenes; there is no host-render fallback."""

import json
import os
import shutil
import subprocess
import tarfile
import time
import uuid
from pathlib import Path

from .media import atomic_json, probe, run, sha256


def render(
    pack: Path,
    output: Path,
    preview=False,
    timeout=1100,
    check_cancelled=lambda: None,
    *,
    stills_only=False,
):
    image = os.environ.get("VIDEO_RENDER_IMAGE", "hackumass-renderer:reference-v8-captions")
    if not image or image.startswith("-"):
        raise ValueError("Invalid renderer image")
    lesson = json.loads((pack / "lesson.json").read_text())
    spatial = (
        lesson.get("presentation") in {"reference_v2", "reference_v3"}
        and lesson.get("format_id") == "space_explainer"
    )
    cpu_limit = "4" if spatial or lesson.get("format_id") == "dialogue_gameplay" else "2"
    # Authored spatial scenes rasterize substantially more geometry; keep an explicit cap.
    if spatial and timeout == 1100:
        timeout = 1600
    name = "lesson-" + uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=True)
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--user",
        "1000:1000",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--cpus",
        cpu_limit,
        "--memory",
        "4g",
        "--pids-limit",
        "256",
        "--shm-size",
        "512m",
        "--log-driver",
        "local",
        "--log-opt",
        "max-size=10m",
        "--log-opt",
        "max-file=2",
        "--ulimit",
        "fsize=1073741824:1073741824",
        "--tmpfs",
        "/tmp:rw,nosuid,size=1536m,mode=1777",
        "--tmpfs",
        "/output:rw,nosuid,noexec,size=2048m,uid=1000,gid=1000",
        "--mount",
        f"type=bind,src={pack.resolve()},dst=/job,readonly",
        "-e",
        f"RENDER_SCALE={'0.5' if preview else '1'}",
        "-e",
        f"RENDER_STILLS_ONLY={int(stills_only)}",
        "--entrypoint",
        "/bin/sh",
        image,
        "-c",
        "node /opt/renderer/render.mjs; result=$?; echo $result > /tmp/render-exit; sleep 600",
    ]
    try:
        run(command, timeout=45)
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            check_cancelled()
            result = subprocess.run(
                ["docker", "exec", name, "cat", "/tmp/render-exit"], capture_output=True, timeout=10
            )
            if result.returncode == 0:
                if result.stdout.strip() != b"0":
                    result = run(["docker", "logs", "--tail", "80", name])
                    logs = (result.stdout + result.stderr).decode(errors="replace")
                    (output / "renderer.log").write_text(logs[:30000])
                    raise RuntimeError("RENDER_FAILED: inspect private renderer.log")
                # Docker Desktop cp does not expose tmpfs contents. Stream from inside.
                process = subprocess.Popen(
                    ["docker", "exec", name, "tar", "-C", "/output", "-cf", "-", "."],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                total = 0
                try:
                    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                        for member in archive:
                            if member.isdir() and member.name in {".", "./"}:
                                continue
                            relative = Path(member.name)
                            total += member.size
                            if (
                                not member.isfile()
                                or relative.is_absolute()
                                or ".." in relative.parts
                                or len(relative.parts) != 1
                                or total > 500_000_000
                            ):
                                raise ValueError("Unsafe renderer archive")
                            target = output / relative.name
                            if target.is_symlink():
                                raise ValueError("Unsafe output target")
                            with archive.extractfile(member) as source, target.open("wb") as dest:
                                shutil.copyfileobj(source, dest, length=1024 * 1024)
                    process.wait(timeout=30)
                    if process.returncode:
                        raise RuntimeError("OUTPUT_COPY_FAILED")
                finally:
                    if process.poll() is None:
                        process.kill()
                report = (
                    {"media_checks": "stills_only"}
                    if stills_only
                    else validate_output(
                        output,
                        preview,
                        minimum_duration=20 if lesson["format_id"] == "math_explainer" else 30,
                    )
                )
                report["renderer_image_id"] = (
                    run(["docker", "inspect", "--format", "{{.Image}}", name])
                    .stdout.decode()
                    .strip()
                )
                atomic_json(output / "quality.json", report)
                return report
            time.sleep(2)
        raise TimeoutError("RENDER_TIMEOUT")
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)


def validate_output(output, preview=False, *, minimum_duration=30):
    video = output / "lesson.mp4"
    if video.is_symlink() or not video.is_file() or not 1000 < video.stat().st_size < 500_000_000:
        raise ValueError("Invalid output file")
    data = probe(video)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    a = next(s for s in data["streams"] if s["codec_type"] == "audio")
    if v["codec_name"] == "h264" and v["pix_fmt"] == "yuvj420p":
        normalized = output / "normalized.mp4"
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                video,
                "-vf",
                "scale=in_range=pc:out_range=tv",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-color_range",
                "tv",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                normalized,
            ],
            timeout=180,
        )
        os.replace(normalized, video)
        data = probe(video)
        v = next(s for s in data["streams"] if s["codec_type"] == "video")
        a = next(s for s in data["streams"] if s["codec_type"] == "audio")
    duration = float(data["format"]["duration"])
    expected = (540, 960) if preview else (1080, 1920)
    if (
        (v["width"], v["height"]) != expected
        or v["codec_name"] != "h264"
        or v["pix_fmt"] != "yuv420p"
        or v["avg_frame_rate"] != "30/1"
    ):
        raise ValueError("Unexpected video profile")
    if (
        a["codec_name"] != "aac"
        or a["sample_rate"] != "48000"
        or not minimum_duration <= duration <= 60
    ):
        raise ValueError("Unexpected audio/duration")
    measured = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            video,
            "-vn",
            "-af",
            "loudnorm=I=-16:TP=-1:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        timeout=60,
    ).stderr.decode()
    levels, _ = json.JSONDecoder().raw_decode(measured[measured.rfind("{") :])
    loudness, peak = float(levels["input_i"]), float(levels["input_tp"])
    if not -19 <= loudness <= -13 or not peak <= -0.5:
        raise ValueError("Final narration loudness/peak outside review limits")
    for f in output.iterdir():
        if f.is_symlink() or not f.is_file() or f.stat().st_size > 500_000_000:
            raise ValueError("Unsafe renderer output")
    report = {
        "schema_version": "1",
        "duration_seconds": duration,
        "width": v["width"],
        "height": v["height"],
        "codec": v["codec_name"],
        "pixel_format": v["pix_fmt"],
        "fps": 30,
        "audio_codec": a["codec_name"],
        "audio_sample_rate": int(a["sample_rate"]),
        "integrated_loudness_lufs": loudness,
        "true_peak_dbfs": peak,
        "sha256": sha256(video),
        "media_checks": "passed",
        "human_review": "pending",
        "iphone_playback": "unverified",
        "preview": preview,
    }
    atomic_json(output / "quality.json", report)
    return report
