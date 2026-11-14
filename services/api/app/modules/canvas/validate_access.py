"""M1 check: can the configured own-account token list this student's courses?

Run from services/api:

    python3 -m app.modules.canvas.validate_access            # prints course names
    python3 -m app.modules.canvas.validate_access --redact   # counts only (safe to paste)

Reads CANVAS_* from the environment, falling back to the gitignored file
services/api/.env.canvas.local. Read-only: two GET endpoints, nothing is
written to Canvas or to disk.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .client.http import CanvasAuthError, CanvasClient, CanvasError
from .config import CanvasConfigError, CanvasSettings, read_env_file

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env.canvas.local"


def list_current_courses(client: CanvasClient) -> list[dict]:
    """Active student enrollments. M2 refines 'current' using term dates."""
    return list(
        client.paginate(
            "/api/v1/courses",
            [
                ("enrollment_type", "student"),
                ("enrollment_state", "active"),
                ("include[]", "term"),
            ],
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--redact", action="store_true", help="print counts only")
    args = parser.parse_args(argv)

    env = {**read_env_file(args.env_file), **os.environ}
    try:
        settings = CanvasSettings.from_env(env)
    except CanvasConfigError as err:
        print(f"config error: {err}", file=sys.stderr)
        return 2

    print(f"institution origin : {settings.institution_origin}")
    print(f"available modes    : {', '.join(settings.available_modes())}")
    if not settings.dev_token:
        print("no CANVAS_DEV_TOKEN configured; nothing to validate live (upload mode only)")
        return 1

    client = CanvasClient(
        settings.institution_origin,
        settings.developer_token_for(settings.dev_token_app_user_id or ""),
    )
    try:
        me = client.get("/api/v1/users/self")
        courses = list_current_courses(client)
    except CanvasAuthError as err:
        print(f"FAILED: {err}. Token is wrong, expired or revoked.", file=sys.stderr)
        return 1
    except CanvasError as err:
        print(f"FAILED: {err}", file=sys.stderr)
        return 1

    print(f"token accepted     : yes (Canvas user id {'<redacted>' if args.redact else me.get('id')})")
    print(f"bound app user     : {settings.dev_token_app_user_id}")
    print(f"active student courses: {len(courses)}")
    if not args.redact:
        for course in courses:
            term = (course.get("term") or {}).get("name", "?")
            print(
                f"  - [{course.get('id')}] {course.get('name', '<restricted>')}"
                f" | term: {term} | tz: {course.get('time_zone', '?')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
