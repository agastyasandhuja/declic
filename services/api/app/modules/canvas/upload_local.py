"""Upload-fallback CLI: register local course files as private demo sources.

Run from services/api:

    python3 -m app.modules.canvas.upload_local \
        --user-id <test app user id> --course "CS 187 Data Structures" syllabus.pdf slides.pptx

Files are copied into the gitignored private directory (.local/academics at
the repo root by default). Nothing is sent anywhere.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .ingestion.uploads import UploadRejected, store_upload

DEFAULT_STORAGE = Path(__file__).resolve().parents[5] / ".local" / "academics"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user-id", required=True, help="app user the files belong to")
    parser.add_argument("--course", required=True, help="course label for these files")
    parser.add_argument("--storage-dir", type=Path, default=DEFAULT_STORAGE)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)

    failures = 0
    for path in args.files:
        try:
            record, created = store_upload(
                user_id=args.user_id,
                course_label=args.course,
                filename=path.name,
                data=path.read_bytes(),
                storage_dir=args.storage_dir,
            )
        except (UploadRejected, OSError) as err:
            failures += 1
            print(f"rejected  {path.name}: {err}", file=sys.stderr)
            continue
        state = "stored   " if created else "unchanged"
        print(f"{state} {path.name} -> {record['source_id']} (course {record['course_id']}, mode upload/demo)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
