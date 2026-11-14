"""Server-side Gemini configuration (owner: Amogh).

Reads GEMINI_API_KEY and GEMINI_MODEL from the backend environment, falling
back to the gitignored file services/api/.env.gemini.local. The key is wrapped
so it cannot leak through logs, and it is never sent to mobile, the renderer,
or into a prompt. See .env.example in this directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# Reuse the credential wrapper and env reader from the canvas module (also Amogh's).
from ..canvas.config import Secret, read_env_file


class GeminiConfigError(ValueError):
    """Configuration missing or invalid. Messages never contain the key."""


@dataclass(frozen=True)
class GeminiSettings:
    api_key: Secret
    model: str
    # Seconds to wait for one generateContent call. Newer "thinking" models can
    # be slow on a cold call, so this is generous and overridable via GEMINI_TIMEOUT.
    timeout_seconds: float = 120.0
    # Gemini 3 models default to "high" thinking, which is slow (minutes per call)
    # and needless for fact extraction. "low" keeps it fast; override via
    # GEMINI_THINKING_LEVEL. Empty string means: do not send the field at all.
    thinking_level: str = "low"
    # The stable REST base. Overridable only for tests, never for secrets.
    api_base: str = "https://generativelanguage.googleapis.com/v1beta"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "GeminiSettings":
        key = (env.get("GEMINI_API_KEY") or "").strip()
        if not key:
            raise GeminiConfigError("GEMINI_API_KEY is not set")
        model = (env.get("GEMINI_MODEL") or "").strip()
        if not model:
            raise GeminiConfigError(
                "GEMINI_MODEL is not set (e.g. a Flash model id your key supports; "
                "run list_models to see available names)"
            )
        base = (env.get("GEMINI_API_BASE") or cls.api_base).strip().rstrip("/")
        try:
            timeout = float(env.get("GEMINI_TIMEOUT") or cls.timeout_seconds)
        except ValueError:
            timeout = cls.timeout_seconds
        thinking = env.get("GEMINI_THINKING_LEVEL")
        thinking = cls.thinking_level if thinking is None else thinking.strip()
        return cls(
            api_key=Secret(key),
            model=model,
            timeout_seconds=timeout,
            thinking_level=thinking,
            api_base=base,
        )


DEFAULT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env.gemini.local"


def load_settings(env_file: Path | None = None, environ: Mapping[str, str] | None = None) -> GeminiSettings:
    import os

    file_values = read_env_file(env_file or DEFAULT_ENV_FILE)
    merged = {**file_values, **(dict(environ) if environ is not None else os.environ)}
    return GeminiSettings.from_env(merged)
