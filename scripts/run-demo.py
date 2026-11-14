#!/usr/bin/env python3
"""Run the cloud-backed demo from this checkout's locked Python environment."""

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "services/api/.venv/bin/python"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["api", "workers", "init", "check"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not PYTHON.exists():
        parser.error(
            "Create the locked environment first: cd services/api && uv sync --locked"
        )
    env = dict(os.environ, PYTHONPATH=str(ROOT / "services/api"))
    if args.command == "api":
        command = [
            str(PYTHON),
            "-m",
            "uvicorn",
            "app.full_runtime:create_app",
            "--factory",
            "--host",
            "0.0.0.0",
            "--port",
            str(args.port),
        ]
    elif args.command == "workers":
        command = [str(PYTHON), "-m", "app.workers.demo"]
    else:
        command = [str(PYTHON), "-m", "app.core.demo_setup", args.command]
    raise SystemExit(subprocess.call(command, cwd=ROOT, env=env))


if __name__ == "__main__":
    main()
