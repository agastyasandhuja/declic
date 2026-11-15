"""One bounded, secret-free render. Run at most two instances on the demo Mac."""

import argparse
import hashlib
import json
import subprocess
import uuid
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[3]


def source_digest():
    paths = [
        *sorted((SOURCE / "src").glob("*")),
        SOURCE / "render.mjs",
        ROOT / "services/renderer/src/PopCaptions.tsx",
        ROOT / "services/renderer/experiments/voxel-story/src/ModelKit.ts",
    ]
    return hashlib.sha256(b"".join(p.read_bytes() for p in paths)).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["stills", "video"])
    parser.add_argument("--id", required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--image", default="hackumass-renderer:reference-v10-dialogue")
    args = parser.parse_args()
    if not args.id.replace("_", "").replace("-", "").isalnum() or len(args.id) > 100:
        parser.error("Invalid lesson ID")
    work = args.work.resolve()
    pack = work / "pack" / args.id
    if not (pack / "manifest.json").is_file():
        parser.error("Prepare and validate the pack first")
    output = work / "output" / args.id
    output.mkdir(parents=True, exist_ok=True)
    if args.mode == "stills":
        for name in ("contact-sheet.jpg", "contact-sheet-provenance.json"):
            (output / name).unlink(missing_ok=True)
    name = f"jensen-render-{uuid.uuid4().hex[:12]}"
    command = [
        "docker",
        "run",
        "--rm",
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
        "4",
        "--memory",
        "3g",
        "--pids-limit",
        "256",
        "--shm-size",
        "512m",
        "--ulimit",
        "fsize=268435456:268435456",
        "--tmpfs",
        "/tmp:rw,nosuid,size=1024m,mode=1777",
        "--mount",
        f"type=bind,src={SOURCE},dst=/opt/renderer/demo,readonly",
        "--mount",
        f"type=bind,src={ROOT}/services/renderer/src/PopCaptions.tsx,dst=/opt/renderer/PopCaptions.tsx,readonly",
        "--mount",
        f"type=bind,src={ROOT}/services/renderer/experiments/voxel-story/src/ModelKit.ts,dst=/opt/renderer/ModelKit.ts,readonly",
        "--mount",
        f"type=bind,src={args.vendor.resolve()},dst=/vendor/three.module.js,readonly",
        "--mount",
        f"type=bind,src={pack},dst=/job/{args.id},readonly",
        "--mount",
        f"type=bind,src={output},dst=/output",
        "-e",
        f"DEMO_MODE={args.mode}",
        "-e",
        f"DEMO_ID={args.id}",
        "-e",
        f"DEMO_SOURCE={source_digest()}",
        "--entrypoint",
        "node",
        args.image,
        "/opt/renderer/demo/render.mjs",
    ]
    try:
        subprocess.run(command, check=True, timeout=3600)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        subprocess.run(["docker", "stop", name], check=False, timeout=20)
        raise
    if args.mode == "video":
        from app.modules.videos.rendering import validate_output

        # Normalize only delivered audio; do not synthesize voices again or
        # re-encode the rendered picture. Review binds the resulting MP4 hash.
        normalized = output / "audio-normalized.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(output / "lesson.mp4"),
                "-c:v",
                "copy",
                "-af",
                "loudnorm=I=-16:TP=-1:LRA=11",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-movflags",
                "+faststart",
                str(normalized),
            ],
            check=True,
            timeout=180,
        )
        normalized.replace(output / "lesson.mp4")
        report = validate_output(output)
        report["audio_processing"] = "loudnorm_I-16_TP-1_LRA11"
        if (output / "lesson.mp4").stat().st_size > 45 * 1024 * 1024:
            raise ValueError(
                "Video exceeds 45 MiB delivery budget; re-encode before publication"
            )
        (output / "quality.json").write_text(json.dumps(report, indent=2))
        print(
            json.dumps(
                {
                    "lesson_id": args.id,
                    "media_checks": report["media_checks"],
                    "duration": report["duration_seconds"],
                    "review_status": "pending",
                }
            )
        )


if __name__ == "__main__":
    main()
