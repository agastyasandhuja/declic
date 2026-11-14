"""List the Gemini models your API key can use, so you can pick the exact Flash
model id for GEMINI_MODEL.

Run from services/api:

    python3 -m app.modules.curriculum.list_models
"""

from __future__ import annotations

import sys

from .client.gemini import GeminiClient, GeminiError
from .config import GeminiConfigError, GeminiSettings, load_settings


def main() -> int:
    try:
        # Model id is not needed just to list; fill a placeholder if unset.
        try:
            settings = load_settings()
        except GeminiConfigError as err:
            if "GEMINI_MODEL" in str(err):
                import os
                from .config import DEFAULT_ENV_FILE
                from ..canvas.config import read_env_file

                env = {**read_env_file(DEFAULT_ENV_FILE), **os.environ, "GEMINI_MODEL": "placeholder"}
                settings = GeminiSettings.from_env(env)
            else:
                raise
    except GeminiConfigError as err:
        print(f"config error: {err}", file=sys.stderr)
        print("Set GEMINI_API_KEY in services/api/.env.gemini.local", file=sys.stderr)
        return 2

    try:
        models = GeminiClient(settings).list_models()
    except GeminiError as err:
        print(f"FAILED: {err}", file=sys.stderr)
        return 1

    flash = [m for m in models if "flash" in m.get("name", "").lower()]
    print(f"{len(models)} models available to this key. Flash models:")
    for model in flash or models:
        name = model.get("name", "").replace("models/", "")
        methods = ",".join(model.get("supportedGenerationMethods", []))
        marker = "  <- flash" if "flash" in name.lower() else ""
        print(f"  - {name}{marker}  [{methods}]")
    print("\nPut one of these in GEMINI_MODEL (a flash id is recommended).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
