"""Minimal Gemini REST client (owner: Amogh), standard library only.

Uses the stable generateContent endpoint with JSON structured output. The model receives supplied excerpts and optional inline media. It has no
Canvas credentials, tools, arbitrary URL access, or database connection. Its output is untrusted until the backend validates it.

Docs: https://ai.google.dev/gemini-api/docs (generateContent + structured output).
"""

from __future__ import annotations

import base64
import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from ..config import GeminiSettings

# (url, body bytes, headers) -> (status, response bytes). Swapped for a fake in tests.
Transport = Callable[[str, bytes, dict[str, str]], tuple[int, bytes]]


class GeminiError(Exception):
    """A call failed. Messages never contain the API key or full prompt."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class GeminiTimeout(GeminiError):
    """The call exceeded the configured timeout."""


@dataclass(frozen=True)
class GeminiResult:
    text: str
    finish_reason: str
    usage: dict[str, Any]


def _urllib_transport_factory(timeout: float) -> Transport:
    def send(url: str, body: bytes, headers: dict[str, str]) -> tuple[int, bytes]:
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as err:
            return err.code, err.read()
        except (TimeoutError, socket.timeout) as err:
            raise GeminiTimeout(f"Gemini call exceeded {timeout:.0f}s timeout") from err
        except urllib.error.URLError as err:
            if isinstance(err.reason, (TimeoutError, socket.timeout)):
                raise GeminiTimeout(f"Gemini call exceeded {timeout:.0f}s timeout") from err
            raise GeminiError(f"network error contacting Gemini: {err.reason}") from None

    return send


class GeminiClient:
    def __init__(
        self,
        settings: GeminiSettings,
        *,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._transport = transport or _urllib_transport_factory(settings.timeout_seconds)
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"GeminiClient(model={self._settings.model!r})"

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self._settings.api_key.reveal(),
        }

    def list_models(self) -> list[dict[str, Any]]:
        """GET the models this key can use, so the exact Flash id is discoverable."""
        url = f"{self._settings.api_base}/models"
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read())
        except urllib.error.HTTPError as err:
            raise GeminiError(f"Gemini listModels failed ({err.code})", err.code) from None
        except (urllib.error.URLError, ValueError) as err:
            raise GeminiError(f"Gemini listModels error: {err}") from None
        return payload.get("models", [])

    def generate_json(
        self,
        *,
        system_instruction: str,
        user_content: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
        media: tuple[tuple[str, str, bytes], ...] = (),
    ) -> GeminiResult:
        """Ask the model for a single JSON object matching response_schema."""
        generation_config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
            "temperature": temperature,
        }
        # Keep Gemini 3 "thinking" low so a fact-extraction call takes seconds,
        # not minutes. Empty level means leave the model's default in place.
        if self._settings.thinking_level:
            generation_config["thinkingConfig"] = {"thinkingLevel": self._settings.thinking_level}

        parts = [{"text": user_content}]
        for source_id, mime_type, data in media:
            parts.extend([
                {"text": f"Untrusted attachment for source_id {source_id}"},
                {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(data).decode("ascii")}},
            ])
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": generation_config,
            }
        ).encode("utf-8")

        url = f"{self._settings.api_base}/models/{self._settings.model}:generateContent"
        # Retry transient failures: timeouts (cold "thinking" models) and
        # 429/503 rate-limit/overload, with simple backoff between attempts.
        status, raw = 0, b""
        for attempt in range(1, 4):
            try:
                status, raw = self._transport(url, body, self._headers())
            except GeminiTimeout:
                if attempt == 3:
                    raise
                self._sleep(2.0 * attempt)
                continue
            if status in (429, 503) and attempt < 3:
                self._sleep(5.0 * attempt)
                continue
            break
        if status != 200:
            # Surface Google's error "message" if present, but never the key/prompt.
            detail = ""
            try:
                detail = json.loads(raw).get("error", {}).get("message", "")[:200]
            except (ValueError, AttributeError):
                pass
            raise GeminiError(f"Gemini returned {status}: {detail}".strip(), status)

        try:
            payload = json.loads(raw)
            candidate = payload["candidates"][0]
            finish = candidate.get("finishReason", "UNKNOWN")
            parts = candidate["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (ValueError, KeyError, IndexError, TypeError):
            raise GeminiError("Gemini returned an unexpected response shape") from None

        if not text.strip():
            raise GeminiError(f"Gemini returned no content (finishReason={finish})")
        return GeminiResult(text=text, finish_reason=finish, usage=payload.get("usageMetadata", {}))


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse the model's JSON, tolerating code-fence wrapping. Raises GeminiError."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        value = json.loads(cleaned)
    except ValueError:
        raise GeminiError("model output was not valid JSON") from None
    if not isinstance(value, dict):
        raise GeminiError("model output was not a JSON object")
    return value
