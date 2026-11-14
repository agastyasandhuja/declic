"""Read-only Canvas REST client.

Safety properties (see AGENTS.md):
- Only GET exists. There is no method for writing to Canvas.
- Every request, pagination link and redirect must stay on the configured
  institution origin, so the bearer token is never sent to another host.
- Error messages carry status and path only: no token, no query string.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping
from urllib.parse import urlencode, urlsplit

from ..config import Secret

_NEXT_LINK = re.compile(r'<([^>]+)>\s*;\s*rel="next"')
_RETRYABLE = {429, 500, 502, 503, 504}


class CanvasError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class CanvasAuthError(CanvasError):
    """401: token missing, expired or revoked. Connection needs reconnect."""


class CanvasUnavailable(CanvasError):
    """403/404: this resource is not accessible to the student. Record and move on."""


@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]  # lower-cased keys
    body: bytes


Transport = Callable[[str, Mapping[str, str], float], Response]


def _same_origin(url: str, origin: str) -> bool:
    a, b = urlsplit(url), urlsplit(origin)
    return a.scheme == "https" and a.scheme == b.scheme and a.netloc.lower() == b.netloc


class _SameOriginRedirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, origin: str) -> None:
        self._origin = origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _same_origin(newurl, self._origin):
            return None  # surfaces as the 3xx response; token is not forwarded
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def urllib_transport(origin: str) -> Transport:
    opener = urllib.request.build_opener(_SameOriginRedirects(origin))

    def send(url: str, headers: Mapping[str, str], timeout: float) -> Response:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        try:
            with opener.open(request, timeout=timeout) as raw:
                return Response(
                    raw.status, {k.lower(): v for k, v in raw.headers.items()}, raw.read()
                )
        except urllib.error.HTTPError as err:
            return Response(
                err.code, {k.lower(): v for k, v in err.headers.items()}, err.read()
            )
        except urllib.error.URLError as err:
            raise CanvasError(f"network error contacting Canvas: {err.reason}") from None

    return send


class CanvasClient:
    def __init__(
        self,
        origin: str,
        token: Secret,
        *,
        transport: Transport | None = None,
        timeout: float = 20.0,
        max_attempts: int = 3,
        max_pages: int = 50,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._origin = origin
        self._token = token
        self._transport = transport or urllib_transport(origin)
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._max_pages = max_pages
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"CanvasClient(origin={self._origin!r})"

    def _url(self, path: str, params: list[tuple[str, str]] | None) -> str:
        if not path.startswith("/api/v1/"):
            raise CanvasError("only /api/v1/ paths are allowed")
        query = f"?{urlencode(params)}" if params else ""
        return f"{self._origin}{path}{query}"

    def _send(self, url: str) -> Response:
        if not _same_origin(url, self._origin):
            raise CanvasError("refusing request outside the configured Canvas origin")
        path = urlsplit(url).path
        headers = {
            "Authorization": f"Bearer {self._token.reveal()}",
            "Accept": "application/json",
        }
        for attempt in range(1, self._max_attempts + 1):
            response = self._transport(url, headers, self._timeout)
            status = response.status
            throttled = status == 403 and b"Rate Limit Exceeded" in response.body
            if (status in _RETRYABLE or throttled) and attempt < self._max_attempts:
                retry_after = response.headers.get("retry-after", "")
                delay = float(retry_after) if retry_after.isdigit() else 2.0**attempt
                self._sleep(min(delay, 30.0))
                continue
            break
        if 200 <= status < 300:
            return response
        if status == 401:
            raise CanvasAuthError(f"Canvas rejected the credential (401) for {path}", 401)
        if status in (403, 404) and not throttled:
            raise CanvasUnavailable(f"Canvas returned {status} for {path}", status)
        if 300 <= status < 400:
            raise CanvasError(f"refused redirect away from Canvas origin for {path}", status)
        raise CanvasError(f"Canvas returned {status} for {path}", status)

    @staticmethod
    def _json(response: Response) -> Any:
        try:
            return json.loads(response.body)
        except ValueError:
            raise CanvasError("Canvas returned a non-JSON response") from None

    def get(self, path: str, params: list[tuple[str, str]] | None = None) -> Any:
        return self._json(self._send(self._url(path, params)))

    def paginate(
        self, path: str, params: list[tuple[str, str]] | None = None
    ) -> Iterator[Any]:
        """Yield items across pages by following rel="next" Link headers."""
        params = [*(params or []), ("per_page", "50")]
        url: str | None = self._url(path, params)
        for _ in range(self._max_pages):
            if url is None:
                return
            response = self._send(url)
            page = self._json(response)
            if not isinstance(page, list):
                raise CanvasError("expected a list from a paginated Canvas endpoint")
            yield from page
            match = _NEXT_LINK.search(response.headers.get("link", ""))
            url = match.group(1) if match else None
        if url is not None:
            raise CanvasError(f"pagination exceeded {self._max_pages} pages")
