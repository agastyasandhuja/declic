"""End-to-end M3 demo (owner: Amogh):

    student's Canvas courses  ->  real Gemini API call  ->  validated course
                                   profile with evidence and source references

PRIMARY path (default): pulls the signed-in student's live Canvas courses and
syllabi automatically through the authorized token — no manual upload.

    python3 -m app.modules.curriculum.run_demo

FALLBACK path (only when Canvas access is blocked): a course-labeled upload.

    python3 -m app.modules.curriculum.run_demo --source upload --syllabus file.txt --course "Name"

Needs the Canvas token (services/api/.env.canvas.local) for the primary path,
and GEMINI_API_KEY + GEMINI_MODEL (services/api/.env.gemini.local) for both. If
Gemini config is missing, the live call is reported as pending.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..canvas.client.http import CanvasAuthError, CanvasClient, CanvasError
from ..canvas.config import CanvasConfigError, CanvasSettings, read_env_file
from ..canvas.ingestion.uploads import UploadRejected, store_upload
from .client.gemini import GeminiClient, GeminiError
from .config import GeminiConfigError, load_settings
from .extract import build_profile
from .sources import CanvasSourceResolver, SourceResolver

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SYLLABUS = REPO_ROOT / "fixtures" / "academics" / "sample_syllabus_dsa.txt"
DEFAULT_STORAGE = REPO_ROOT / ".local" / "academics"
CANVAS_ENV = REPO_ROOT / "services" / "api" / ".env.canvas.local"


def _print_profile(profile: dict) -> None:
    print(f"\nProfile {profile['profile_id']} revision {profile['revision']} "
          f"({profile['status']}), generated {profile['generated_at']}")
    print(f"Gemini token usage: {profile['usage']}")
    for course in profile["courses"]:
        print(f"\n== Course [{course['import_status']}] {course.get('title') or course['course_id']}")
        if course.get("term") or course.get("timezone"):
            print(f"   term: {course.get('term')} | timezone: {course.get('timezone')}")
        for book in course.get("textbooks", []):
            print(f"   textbook: {book['title']} (ed. {book['edition']}, ISBN {book['isbn']}) "
                  f"[sources: {', '.join(book['source_refs']) or 'none'}]")
        for unit in [u for u in profile["units"] if u["course_id"] == course["course_id"]]:
            print(f"   Unit {unit['order']}: {unit['title']}  [sources: {', '.join(unit['source_refs']) or 'none'}]")
            for objective in unit["objectives"]:
                print(f"      - {objective}")
        for exam in [a for a in profile["assessments"] if a["course_id"] == course["course_id"]]:
            when = exam["scheduled"]
            date_str = when["timestamp"] or when["date"] or "no date"
            print(f"   {exam['kind']}: {exam['title']} -> {date_str} "
                  f"({when['precision']}/{when['evidence_status']}, scope {exam['scope_status']}) "
                  f"[sources: {', '.join(exam['source_refs']) or 'none'}]")
    if profile["warnings"]:
        print("\nWarnings:")
        for warning in profile["warnings"]:
            print(f"   ! {warning}")


def _canvas_resolver(user_id: str) -> CanvasSourceResolver:
    import os

    env = {**read_env_file(CANVAS_ENV), **os.environ}
    settings = CanvasSettings.from_env(env)
    if not settings.dev_token:
        raise CanvasConfigError("no Canvas token configured; use --source upload instead")
    client = CanvasClient(settings.institution_origin, settings.developer_token_for(settings.dev_token_app_user_id or ""))
    print(f"[1/2] Pulling live Canvas courses from {settings.institution_origin} ...")
    return CanvasSourceResolver(client)


def _upload_resolver(user_id: str, args) -> SourceResolver:
    record, created = store_upload(
        user_id=user_id, course_label=args.course, filename=args.syllabus.name,
        data=args.syllabus.read_bytes(), storage_dir=args.storage_dir,
    )
    print(f"[1/2] (fallback) Uploaded {args.syllabus.name} -> {record['source_id']} "
          f"(course {record['course_id']}, {'new' if created else 'reused'})")
    return SourceResolver(user_id, args.storage_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=["canvas", "upload"], default="canvas",
                        help="canvas (default, auto-pull live courses) or upload (fallback)")
    parser.add_argument("--syllabus", type=Path, default=DEFAULT_SYLLABUS)
    parser.add_argument("--course", default="Introduction to Data Structures (DEMO 187)")
    parser.add_argument("--user-id", default="demo-user-amogh")
    parser.add_argument("--storage-dir", type=Path, default=DEFAULT_STORAGE)
    args = parser.parse_args(argv)

    # Step 1: get the student's sources (live Canvas by default).
    try:
        if args.source == "canvas":
            resolver = _canvas_resolver(args.user_id)
        else:
            resolver = _upload_resolver(args.user_id, args)
    except (CanvasConfigError, CanvasAuthError, CanvasError) as err:
        print(f"Canvas source failed: {err}", file=sys.stderr)
        print("Tip: ensure services/api/.env.canvas.local has a valid token, "
              "or use --source upload.", file=sys.stderr)
        return 2
    except (UploadRejected, OSError) as err:
        print(f"upload failed: {err}", file=sys.stderr)
        return 2

    # Step 2: real Gemini extraction over those sources.
    try:
        settings = load_settings()
    except GeminiConfigError as err:
        print(f"\n[2/2] LIVE GEMINI CALL: PENDING — {err}")
        print("Configure services/api/.env.gemini.local (GEMINI_API_KEY, GEMINI_MODEL) and rerun.")
        return 3

    print(f"[2/2] Calling Gemini model '{settings.model}' (timeout {settings.timeout_seconds:.0f}s) ...")
    try:
        profile = build_profile(args.user_id, resolver, GeminiClient(settings), args.storage_dir)
    except ValueError as err:
        print(f"no sources to extract: {err}", file=sys.stderr)
        return 2
    except GeminiError as err:
        print(f"Gemini call failed: {err}", file=sys.stderr)
        return 1
    _print_profile(profile)

    if any(c["import_status"] == "ready" for c in profile["courses"]):
        print("\nLIVE GEMINI CALL: VERIFIED (a real API response was received and validated).")
        return 0
    print("\nLIVE GEMINI CALL: FAILED — no course was extracted. See the warnings above.")
    print("If it was a timeout, raise GEMINI_TIMEOUT or try a faster model such as gemini-2.5-flash.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
