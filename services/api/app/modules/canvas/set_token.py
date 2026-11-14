"""Store a Canvas access token into the gitignored env file, without the token
appearing on screen or in shell history.

Run from services/api:

    python3 -m app.modules.canvas.set_token

Paste the token when prompted (it stays hidden), press Enter, and this writes
services/api/.env.canvas.local with the UMass base URL and the bound test user.
Nothing is printed back and nothing leaves your machine.
"""

from __future__ import annotations

import sys
from getpass import getpass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[3] / ".env.canvas.local"
BASE_URL = "https://umamherst.instructure.com"
APP_USER = "demo-user-amogh"


def main() -> int:
    token = getpass("Paste your Canvas access token (hidden), then Enter: ").strip()
    if not token:
        print("No token entered; nothing written.", file=sys.stderr)
        return 1
    if " " in token or "\n" in token:
        print("That does not look like a token (contains spaces).", file=sys.stderr)
        return 1

    ENV_FILE.write_text(
        f"CANVAS_BASE_URL={BASE_URL}\n"
        f"CANVAS_DEV_TOKEN={token}\n"
        f"CANVAS_DEV_TOKEN_APP_USER_ID={APP_USER}\n",
        encoding="utf-8",
    )
    ENV_FILE.chmod(0o600)
    print(f"Saved to {ENV_FILE.name} (git-ignored). Token not displayed.")
    print("Next: python3 -m app.modules.canvas.validate_access --redact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
