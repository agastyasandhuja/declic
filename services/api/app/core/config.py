from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlparse

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="API_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    environment: Literal["development", "test", "fixture", "production"] = "development"
    persistence: Literal["mongodb", "fixture_sqlite"] = "mongodb"
    mongodb_uri: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("MONGODB_URI", "API_MONGODB_URI", "mongodb_uri")
    )
    mongodb_database: str = Field(
        default="hackumass",
        pattern=r"^[a-zA-Z0-9_-]{1,63}$",
        validation_alias=AliasChoices(
            "MONGODB_DATABASE", "API_MONGODB_DATABASE", "mongodb_database"
        ),
    )
    supabase_url: str | None = Field(
        default=None, validation_alias=AliasChoices("SUPABASE_URL", "supabase_url")
    )
    supabase_publishable_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_PUBLISHABLE_KEY", "supabase_publishable_key"),
    )
    catalog_cursor_secret: SecretStr | None = Field(default=None, min_length=32)
    fixture_database_path: Path = Path(".local/api-fixture.db")
    fixture_token: SecretStr | None = None
    cors_origins: list[str] = Field(default_factory=list)
    max_body_bytes: int = Field(default=128_000, ge=1024, le=1_000_000)
    session_idle_seconds: int = Field(default=1800, ge=60, le=86400)
    max_page_size: int = Field(default=20, ge=1, le=50)
    max_unseen_slots: int = Field(default=40, ge=20, le=100)
    quiz_after_study_exposures: int = Field(default=2, ge=1, le=10)
    exposure_seconds: int = Field(default=10, ge=1, le=60)
    rate_limit_per_minute: int = Field(default=240, ge=10, le=10000)

    @model_validator(mode="after")
    def safe_modes(self):
        if self.persistence == "fixture_sqlite" and self.environment not in {"test", "fixture"}:
            raise ValueError("The fake SQLite document adapter requires fixture/test mode")
        if self.persistence == "mongodb":
            if self.mongodb_uri is None:
                raise ValueError("MONGODB_URI is required for MongoDB persistence")
            url = urlparse(self.mongodb_uri.get_secret_value())
            if url.scheme not in {"mongodb", "mongodb+srv"}:
                raise ValueError("Use a MongoDB URI")
            options = {k.lower(): v[-1].lower() for k, v in parse_qs(url.query).items()}
            if any(
                options.get(k) == "true"
                for k in ("tlsinsecure", "tlsallowinvalidcertificates", "tlsallowinvalidhostnames")
            ):
                raise ValueError("MongoDB TLS verification cannot be disabled")
            if self.environment == "production" and (
                options.get("tls") == "false"
                or options.get("ssl") == "false"
                or (url.scheme != "mongodb+srv" and options.get("tls") != "true")
            ):
                raise ValueError("Production MongoDB requires verified TLS")
        if self.fixture_token is not None:
            if self.environment not in {"fixture", "test"}:
                raise ValueError("Fixture authentication is unavailable outside fixture/test mode")
            if len(self.fixture_token.get_secret_value()) < 32:
                raise ValueError("Use a generated fixture token of at least 32 characters")
        if "*" in self.cors_origins:
            raise ValueError("Configure explicit CORS origins")
        if self.environment == "production":
            if any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("Production CORS origins must use HTTPS")
        return self
