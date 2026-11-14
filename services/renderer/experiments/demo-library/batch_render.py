"""Two-slot local render queue, with explicit digest-bound frame approval."""

import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from run import SOURCE, source_digest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected(work, lesson_id):
    pack = work / "pack" / lesson_id
    return {
        "lesson_sha256": sha(pack / "lesson.json"),
        "pack_sha256": sha(pack / "manifest.json"),
        "renderer_source": source_digest(),
    }


def current(work, lesson_id, mode):
    output = work / "output" / lesson_id
    try:
        proof = json.loads((output / f"{mode}-provenance.json").read_text())
        if any(proof.get(k) != v for k, v in expected(work, lesson_id).items()):
            return False
        if mode == "video":
            quality = json.loads((output / "quality.json").read_text())
            return quality.get("media_checks") == "passed" and quality.get(
                "sha256"
            ) == sha(output / "lesson.mp4")
        return all(
            (output / entry["file"]).is_file()
            for entry in json.loads((output / "frame-index.json").read_text())
        )
    except (OSError, ValueError, KeyError):
        return False


def frames(work, lesson_id):
    output = work / "output" / lesson_id
    return {
        entry["file"]: sha(output / entry["file"])
        for entry in json.loads((output / "frame-index.json").read_text())
    }


def approved(work, lesson_id):
    try:
        data = json.loads((work / "approvals" / f"{lesson_id}.json").read_text())
        return (
            data.get("reviewer")
            and data.get("frames_reviewed") is True
            and data.get("provenance") == expected(work, lesson_id)
            and data.get("frames") == frames(work, lesson_id)
        )
    except (OSError, ValueError, KeyError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run", "approve"])
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--vendor", type=Path)
    parser.add_argument("--id")
    parser.add_argument("--reviewer")
    parser.add_argument("--notes")
    parser.add_argument("--deadline", type=int, default=7200)
    args = parser.parse_args()
    work = args.work.resolve()
    ids = sorted(
        p.name for p in (work / "pack").iterdir() if (p / "manifest.json").is_file()
    )
    if args.command == "approve":
        if args.id not in ids or not args.reviewer or not args.notes:
            parser.error(
                "approve needs an existing ID, named reviewer and actual review notes"
            )
        if not current(work, args.id, "stills"):
            parser.error("Current source/pack stills must exist before approval")
        folder = work / "approvals"
        folder.mkdir(exist_ok=True)
        (folder / f"{args.id}.json").write_text(
            json.dumps(
                {
                    "reviewer": args.reviewer,
                    "notes": args.notes,
                    "frames_reviewed": True,
                    "provenance": expected(work, args.id),
                    "frames": frames(work, args.id),
                },
                indent=2,
            )
        )
        print(json.dumps({"lesson_id": args.id, "frame_review_recorded": True}))
        return
    if not args.vendor:
        parser.error("run requires --vendor")
    lock = (work / "render-queue.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("A render queue already owns this workspace")
    (work / "logs").mkdir(exist_ok=True)

    def execute(lesson_id, mode):
        command = [
            sys.executable,
            str(SOURCE / "run.py"),
            mode,
            "--id",
            lesson_id,
            "--work",
            str(work),
            "--vendor",
            str(args.vendor.resolve()),
        ]
        with (work / "logs" / f"{lesson_id}-{mode}.log").open("w") as log:
            subprocess.run(
                command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3700
            )
        if mode == "stills":
            subprocess.run(
                [
                    "python3",
                    str(SOURCE / "contact_sheet.py"),
                    str(work / "output" / lesson_id),
                ],
                check=True,
                timeout=60,
            )
        return lesson_id, mode

    active, failed = {}, set()
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        while time.monotonic() - started < args.deadline:
            for future in list(active):
                if not future.done():
                    continue
                lesson_id, mode = active.pop(future)
                try:
                    future.result()
                    print(
                        json.dumps(
                            {
                                "lesson_id": lesson_id,
                                "stage": mode,
                                "state": "completed",
                            }
                        ),
                        flush=True,
                    )
                except (OSError, subprocess.SubprocessError):
                    failed.add((lesson_id, mode))
                    print(
                        json.dumps(
                            {
                                "lesson_id": lesson_id,
                                "stage": mode,
                                "state": "failed",
                                "log": str(work / "logs" / f"{lesson_id}-{mode}.log"),
                            }
                        ),
                        flush=True,
                    )
            occupied = {lesson_id for lesson_id, _ in active.values()}
            candidates = [
                (lesson_id, "stills")
                for lesson_id in ids
                if not current(work, lesson_id, "stills")
            ]
            candidates += [
                (lesson_id, "video")
                for lesson_id in ids
                if not current(work, lesson_id, "video") and approved(work, lesson_id)
            ]
            for lesson_id, mode in candidates:
                if len(active) >= 2:
                    break
                if lesson_id in occupied or (lesson_id, mode) in failed:
                    continue
                active[pool.submit(execute, lesson_id, mode)] = (lesson_id, mode)
                occupied.add(lesson_id)
                print(
                    json.dumps(
                        {"lesson_id": lesson_id, "stage": mode, "state": "started"}
                    ),
                    flush=True,
                )
            if all(current(work, lesson_id, "video") for lesson_id in ids):
                print(json.dumps({"complete": len(ids)}), flush=True)
                return
            if not active and failed:
                raise SystemExit(
                    "Repair failed tasks and rerun; completed artifacts are reused"
                )
            time.sleep(3)
    raise SystemExit("Queue deadline reached; completed artifacts retained")


if __name__ == "__main__":
    main()
