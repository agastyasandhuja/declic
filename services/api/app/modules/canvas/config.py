"""Server-side Canvas configuration.

Values come from the backend process environment (or a gitignored env file
loaded by a local CLI). Nothing here is ever sent to mobile, Gemini, logs or
fixtures. See .env.example in this directory for the variable names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit


class CanvasConfigError(ValueError):
    """Configuration is missing or unsafe. Messages never contain secrets."""


class Secret:
    """Wraps a credential so it cannot leak through repr/str/format."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret(***)"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return "***"


def normalize_origin(raw: str) -> str:
    """Return 'https://host[:port]' or raise. Rejects http, paths and userinfo."""
    parts = urlsplit(raw.strip())
    if parts.scheme != "https":
        raise CanvasConfigError("CANVAS_BASE_URL must start with https://")
    if not parts.hostname or parts.username or parts.password:
        raise CanvasConfigError("CANVAS_BASE_URL must be a plain https origin")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise CanvasConfigError(
            "CANVAS_BASE_URL must be the origin only, e.g. https://school.instructure.com"
        )
    port = f":{parts.port}" if parts.port and parts.port != 443 else ""
    return f"https://{parts.hostname.lower()}{port}"


def read_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE lines. Missing file returns an empty mapping."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


@dataclass(frozen=True)
class CanvasSettings:
    institution_origin: str
    dev_token: Secret | None = None
    dev_token_app_user_id: str | None = None
    oauth_client_id: str | None = None
    oauth_client_secret: Secret | None = field(default=None)
    oauth_redirect_uri: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "CanvasSettings":
        def get(name: str) -> str | None:
            value = (env.get(name) or "").strip()
            return value or None

        base = get("CANVAS_BASE_URL")
        if not base:
            raise CanvasConfigError("CANVAS_BASE_URL is not set")
        token = get("CANVAS_DEV_TOKEN")
        bound_user = get("CANVAS_DEV_TOKEN_APP_USER_ID")
        if token and not bound_user:
            raise CanvasConfigError(
                "CANVAS_DEV_TOKEN requires CANVAS_DEV_TOKEN_APP_USER_ID "
                "(the single test app user the token is bound to)"
            )
        secret = get("CANVAS_OAUTH_CLIENT_SECRET")
        return cls(
            institution_origin=normalize_origin(base),
            dev_token=Secret(token) if token else None,
            dev_token_app_user_id=bound_user,
            oauth_client_id=get("CANVAS_OAUTH_CLIENT_ID"),
            oauth_client_secret=Secret(secret) if secret else None,
            oauth_redirect_uri=get("CANVAS_OAUTH_REDIRECT_URI"),
        )

    @property
    def oauth_configured(self) -> bool:
        return bool(
            self.oauth_client_id and self.oauth_client_secret and self.oauth_redirect_uri
        )

    def available_modes(self) -> list[str]:
        """Connection modes (contract: CanvasConnection.mode) usable right now."""
        modes = []
        if self.oauth_configured:
            modes.append("oauth")
        if self.dev_token:
            modes.append("developer_token")
        modes.append("upload")
        return modes

    def developer_token_for(self, app_user_id: str) -> Secret:
        """Return the demo token only for the one app user it is bound to."""
        if not self.dev_token:
            raise CanvasConfigError("developer-token mode is not configured")
        if app_user_id != self.dev_token_app_user_id:
            raise PermissionError("developer token is not bound to this app user")
        return self.dev_token
