"""M1 check: can we reach this student's own Canvas courses and their content?

Run from services/api:

    python3 -m app.modules.canvas.validate_access            # live: your real courses
    python3 -m app.modules.canvas.validate_access --redact   # counts only (safe to paste)
    python3 -m app.modules.canvas.validate_access --demo     # synthetic preview, no token

Reads CANVAS_* from the environment, falling back to the gitignored file
services/api/.env.canvas.local. Read-only: a couple of GET endpoints, nothing
is written to Canvas or to disk.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .client.http import CanvasAuthError, CanvasClient, CanvasError
from .config import CanvasConfigError, CanvasSettings, Secret, read_env_file
from .courses import summarize_current_courses

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env.canvas.local"


def _print_courses(client: CanvasClient, redact: bool) -> int:
    courses = summarize_current_courses(client)
    print(f"accessible current courses: {len(courses)}")
    for course in courses:
        print(f"  - {course.one_line()}")
        if not redact and course.syllabus_preview:
            print(f"      syllabus: {course.syllabus_preview}...")
    return len(courses)


def _run_demo() -> int:
    from .demo_data import demo_transport

    print("*** SYNTHETIC DEMO DATA — not a live Canvas sync ***")
    client = CanvasClient("https://canvas.example.edu", Secret("demo"), transport=demo_transport)
    me = client.get("/api/v1/users/self")
    print(f"signed in as       : {me['name']}")
    _print_courses(client, redact=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--redact", action="store_true", help="print counts only")
    parser.add_argument("--demo", action="store_true", help="synthetic preview, no token")
    args = parser.parse_args(argv)

    if args.demo:
        return _run_demo()

    env = {**read_env_file(args.env_file), **os.environ}
    try:
        settings = CanvasSettings.from_env(env)
    except CanvasConfigError as err:
        print(f"config error: {err}", file=sys.stderr)
        return 2

    print(f"institution origin : {settings.institution_origin}")
    print(f"available modes    : {', '.join(settings.available_modes())}")
    if not settings.dev_token:
        print("no CANVAS_DEV_TOKEN configured; nothing to validate live.")
        print("  -> generate a Canvas access token, add it to the env file, and rerun,")
        print("     or use upload mode. Try --demo to preview the output shape.")
        return 1

    client = CanvasClient(
        settings.institution_origin,
        settings.developer_token_for(settings.dev_token_app_user_id or ""),
    )
    try:
        me = client.get("/api/v1/users/self")
        count = _print_courses(client, args.redact)
    except CanvasAuthError as err:
        print(f"FAILED: {err}. Token is wrong, expired or revoked.", file=sys.stderr)
        return 1
    except CanvasError as err:
        print(f"FAILED: {err}", file=sys.stderr)
        return 1

    who = "<redacted>" if args.redact else me.get("id")
    print(f"token accepted     : yes (Canvas user id {who})")
    print(f"bound app user     : {settings.dev_token_app_user_id}")
    return 0 if count else 1


if __name__ == "__main__":
    raise SystemExit(main())
