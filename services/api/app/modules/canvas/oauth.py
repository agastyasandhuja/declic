"""Canvas OAuth2 sign-in ("Log in with your school account").

How it works for a UMass student:
1. Our backend sends the student's browser to Canvas (build_authorization_url).
2. Canvas hands off to the UMass Microsoft sign-in page. The student types
   their NetID password there, never into our app.
3. Canvas redirects back to our callback with a one-time code.
4. Our backend swaps the code for tokens (exchange_code), server-side only.

Requires a developer key (client id + secret) issued by the school's Canvas
admins. Until UMass issues one, this code is untested against real Canvas.

Docs: https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth
"""

from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlencode

from .config import CanvasConfigError, CanvasSettings, Secret

STATE_LIFETIME_SECONDS = 600

# (url, form fields) -> (status, body). Swapped for a fake in tests.
PostForm = Callable[[str, dict[str, str]], tuple[int, bytes]]


class CanvasOAuthError(Exception):
    """Sign-in failed. Messages never contain codes, secrets or tokens."""


@dataclass(frozen=True)
class OAuthTokens:
    access_token: Secret
    refresh_token: Secret | None
    expires_in_seconds: int | None
    external_user_id: str | None


class StateStore:
    """Remembers which app user started each sign-in.

    The state value is random, single-use and short-lived. In-memory for now;
    replace with a database table when the shared API core exists.
    """

    def __init__(self, now: Callable[[], float] = time.time) -> None:
        self._now = now
        self._pending: dict[str, tuple[str, float]] = {}

    def issue(self, app_user_id: str) -> str:
        state = secrets.token_urlsafe(32)
        self._pending[state] = (app_user_id, self._now() + STATE_LIFETIME_SECONDS)
        return state

    def consume(self, state: str) -> str:
        """Return the app user for this state, or raise. Works only once."""
        app_user_id, expires_at = self._pending.pop(state, ("", 0.0))
        if not app_user_id or self._now() > expires_at:
            raise CanvasOAuthError("sign-in session is unknown or expired; start again")
        return app_user_id


def _require_oauth(settings: CanvasSettings) -> None:
    if not settings.oauth_configured:
        raise CanvasConfigError(
            "Canvas OAuth is not configured (needs a school-issued developer key)"
        )


def build_authorization_url(settings: CanvasSettings, state: str) -> str:
    """The Canvas page the student's browser should open to sign in."""
    _require_oauth(settings)
    query = urlencode(
        {
            "client_id": settings.oauth_client_id,
            "response_type": "code",
            "redirect_uri": settings.oauth_redirect_uri,
            "state": state,
        }
    )
    return f"{settings.institution_origin}/login/oauth2/auth?{query}"


def _urllib_post_form(url: str, fields: dict[str, str]) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=urlencode(fields).encode(), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()
    except urllib.error.URLError:
        raise CanvasOAuthError("network error contacting Canvas") from None


def _request_tokens(
    settings: CanvasSettings, grant: dict[str, str], post_form: PostForm
) -> OAuthTokens:
    _require_oauth(settings)
    fields = {
        "client_id": settings.oauth_client_id,
        "client_secret": settings.oauth_client_secret.reveal(),
        **grant,
    }
    status, body = post_form(f"{settings.institution_origin}/login/oauth2/token", fields)
    if status != 200:
        raise CanvasOAuthError(f"Canvas refused the sign-in ({status})")
    try:
        payload = json.loads(body)
        access_token = payload["access_token"]
    except (ValueError, KeyError, TypeError):
        raise CanvasOAuthError("Canvas returned an unexpected sign-in response") from None

    refresh_token = payload.get("refresh_token")
    user_id = (payload.get("user") or {}).get("id")
    return OAuthTokens(
        access_token=Secret(access_token),
        refresh_token=Secret(refresh_token) if refresh_token else None,
        expires_in_seconds=payload.get("expires_in"),
        external_user_id=str(user_id) if user_id is not None else None,
    )


def exchange_code(
    settings: CanvasSettings, code: str, post_form: PostForm = _urllib_post_form
) -> OAuthTokens:
    """Swap the one-time code from the callback for tokens."""
    grant = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.oauth_redirect_uri or "",
    }
    return _request_tokens(settings, grant, post_form)


def refresh_access_token(
    settings: CanvasSettings, refresh_token: Secret, post_form: PostForm = _urllib_post_form
) -> OAuthTokens:
    """Access tokens last about an hour; get a new one without re-login.

    Canvas does not return a new refresh token here; keep using the original.
    """
    grant = {"grant_type": "refresh_token", "refresh_token": refresh_token.reveal()}
    return _request_tokens(settings, grant, post_form)
