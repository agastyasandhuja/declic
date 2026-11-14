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
import os
import sys
from collections import Counter
from pathlib import Path

from ..canvas.client.http import CanvasAuthError, CanvasClient, CanvasError
from ..canvas.config import CanvasConfigError, CanvasSettings, read_env_file
from ..canvas.ingestion.uploads import UploadRejected, store_upload
from .client.gemini import GeminiClient, GeminiError
from .config import GeminiConfigError, load_settings
from .extract import build_profile
from .planning.planner import build_lesson_plans
from .sources import CanvasSourceResolver, SourceResolver
from .store import save_plans

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SYLLABUS = REPO_ROOT / "fixtures" / "academics" / "sample_syllabus_dsa.txt"
DEFAULT_STORAGE = REPO_ROOT / ".local" / "academics"
CANVAS_ENV = REPO_ROOT / "services" / "api" / ".env.canvas.local"


def _attach_timing(profile: dict, resolver) -> None:
    """Compute each course's real-time urgency from live Canvas due dates and
    sort courses most-urgent first. Deterministic; no invented dates."""
    from .timing import course_timing

    for course in profile["courses"]:
        assignments = resolver.assignments_for_course(course["course_id"])
        t = course_timing(assignments)
        course["timing"] = {
            "next_due_name": t.next_due_name,
            "next_due_date": t.next_due_date,
            "days_until_next": t.days_until_next,
            "upcoming_count": t.upcoming_count,
            "urgency": t.urgency,
            "has_undated_exam": t.has_undated_exam,
            "upcoming": [{"name": i.name, "due_date": i.due_at.date().isoformat(),
                          "days_until": i.days_until, "is_exam": i.is_exam} for i in t.upcoming],
        }
    profile["courses"].sort(key=lambda c: c.get("timing", {}).get("urgency", 0.0), reverse=True)


def _print_profile(profile: dict) -> None:
    print(f"\nProfile {profile['profile_id']} revision {profile['revision']} "
          f"({profile['status']}), generated {profile['generated_at']}")
    print(f"Gemini token usage: {profile['usage']}")
    print("(courses ordered by real-time urgency: soonest upcoming work first)")
    for course in profile["courses"]:
        print(f"\n== Course [{course['import_status']}] {course.get('title') or course['course_id']}")
        t = course.get("timing") or {}
        if t.get("days_until_next") is not None:
            exam = " | exam listed (no Canvas date)" if t.get("has_undated_exam") else ""
            print(f"   NEXT DUE in {t['days_until_next']}d: {t['next_due_name']} ({t['next_due_date']}) "
                  f"| {t['upcoming_count']} upcoming | urgency {t['urgency']}{exam}")
        elif t.get("has_undated_exam"):
            print("   no upcoming dated work; an exam is listed without a Canvas date")
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


def _print_plans(plans: list[dict]) -> None:
    for plan in plans:
        print(f"\n== Lesson plan {plan['plan_id']} for course {plan['course_id']} "
              f"({plan['status']}, {len(plan['requests'])} lessons)")
        for lr in plan["requests"]:
            exam = {"explicit": "confirmed exam", "inferred": "maybe exam", "user_confirmed": "confirmed by student", "unknown": "not exam"}[lr["exam_scope_status"]]
            tag = "suggested practice" if lr["evidence_status"] == "suggested_practice" else exam
            print(f"   [{lr['importance']}] {lr['title']} ({lr['target_duration_seconds']}s, {tag})")
            print(f"      goal: {lr['learning_goal']}")
            print(f"      formats: {', '.join(lr['suggested_formats'])} | "
                  f"approaches: {', '.join(lr['teaching_approaches']) or 'n/a'} | "
                  f"sources: {', '.join(lr['source_refs']) or 'none'}")
        for warning in plan.get("warnings", []):
            print(f"   ! {warning}")


def _canvas_resolver(user_id: str) -> CanvasSourceResolver:
    env = {**read_env_file(CANVAS_ENV), **os.environ}
    settings = CanvasSettings.from_env(env)
    if not settings.dev_token:
        raise CanvasConfigError("no Canvas token configured; use --source upload instead")
    client = CanvasClient(settings.institution_origin, settings.developer_token_for(user_id))
    print(f"[1/2] Pulling live Canvas courses from {settings.institution_origin} ...")
    return CanvasSourceResolver(client, owner_user_id=user_id)


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
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--storage-dir", type=Path, default=DEFAULT_STORAGE)
    parser.add_argument("--plan", action="store_true", help="also run M4 Gemini lesson planning")
    args = parser.parse_args(argv)

    if args.user_id is None:
        args.user_id = ({**read_env_file(CANVAS_ENV), **os.environ}.get("CANVAS_DEV_TOKEN_APP_USER_ID")
                        if args.source == "canvas" else None) or "demo-user-amogh"

    # Step 1: get the student's sources (live Canvas by default).
    try:
        if args.source == "canvas":
            resolver = _canvas_resolver(args.user_id)
        else:
            resolver = _upload_resolver(args.user_id, args)
    except (CanvasConfigError, CanvasAuthError, CanvasError, PermissionError) as err:
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
    except (CanvasError, GeminiError) as err:
        print(f"Provider call failed: {type(err).__name__}", file=sys.stderr)
        return 1
    if isinstance(resolver, CanvasSourceResolver):
        _attach_timing(profile, resolver)  # real-time urgency from live due dates
        inventory = Counter((source.resource_type, source.has_text) for source in resolver.list_sources())
        for category in sorted({kind for kind, _ in inventory}):
            usable = inventory[category, True]
            print(f"Inventory {category}: {usable} with text / {usable + inventory[category, False]} total")
    _print_profile(profile)

    if not any(c["import_status"] == "ready" for c in profile["courses"]):
        print("\nLIVE GEMINI CALL: FAILED — no course was extracted. See the warnings above.")
        return 1
    print("\nM3 EXTRACTION: VERIFIED (real Gemini response received and validated).")

    # Step 3 (M4): plan 30-60s lessons across courses with a second Gemini call.
    if not args.plan:
        return 0
    print("\n[3/3] Planning lessons with Gemini ...")
    try:
        plans = build_lesson_plans(profile, GeminiClient(settings), resolver)
    except GeminiError as err:
        print(f"lesson planning failed: {err}", file=sys.stderr)
        return 1
    save_plans(args.storage_dir, args.user_id, plans)
    _print_plans(plans)
    total = sum(len(p["requests"]) for p in plans)
    if total:
        from .handoff import build_profile_ready_event

        event = build_profile_ready_event(profile, plans)
        print(f"\nHandoff event for Agastya: {event['event']} "
              f"(profile {event['profile_id']} rev {event['revision']}, "
              f"{len(event['plan_ids'])} plan(s))")
        print(f"\nM4 LESSON PLANNING: VERIFIED — Gemini proposed {total} lesson objectives "
              f"across {len([p for p in plans if p['requests']])} course(s).")
        return 0
    print("\nM4 LESSON PLANNING: no lessons proposed (courses may lack enough material).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
