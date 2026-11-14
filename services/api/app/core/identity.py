"""Internal consumer seam for Adi's verifier; no signup or JWT implementation here."""

import secrets
from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings
from app.core.errors import APIError


@dataclass(frozen=True)
class Principal:
    user_id: str
    timezone: str = "UTC"


class IdentityVerifier(Protocol):
    def verify_access_token(self, token: str) -> Principal: ...


class UnconfiguredIdentity:
    def verify_access_token(self, token: str) -> Principal:
        raise APIError(503, "AUTH_UNCONFIGURED", "Identity adapter is unavailable", retryable=True)


class FixtureIdentity:
    """Single synthetic user, explicit generated token, forbidden in deployed modes."""

    def __init__(self, settings: Settings):
        if settings.environment not in {"fixture", "test"} or settings.fixture_token is None:
            raise ValueError("Fixture identity requires explicit fixture/test configuration")
        self.token = settings.fixture_token.get_secret_value()

    def verify_access_token(self, token: str) -> Principal:
        if not secrets.compare_digest(token.encode(), self.token.encode()):
            raise APIError(401, "INVALID_TOKEN", "Invalid or expired access token")
        return Principal("user_demo_01", "America/New_York")
