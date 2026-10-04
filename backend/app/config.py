"""Runtime configuration, loaded from environment variables (and backend/.env)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"
# backend/.env, found no matter which directory the API is started from (later files win).
ENV_FILES = (".env", Path(__file__).resolve().parents[1] / ".env")

# GroupWise is designed for Bangladesh first. Expense timestamps are stored as
# local wall-clock time (Asia/Dhaka, UTC+6, no DST) so weekday/weekend and
# time-of-day analytics match how the group actually experiences its spending.
LOCAL_TZ = timezone(timedelta(hours=6), name="Asia/Dhaka")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./groupwise.db"
    cors_origins: str = "http://localhost:3000"
    public_app_url: str = "http://localhost:3000"

    # Tokens issued by this service (local accounts + demo sessions)
    jwt_secret: str = DEV_JWT_SECRET
    jwt_ttl_hours: int = 72
    allow_local_auth: bool = True

    # Supabase Auth (optional). When configured, Supabase-issued access tokens are accepted.
    supabase_url: str | None = None
    supabase_jwt_secret: str | None = None  # legacy HS256 projects; otherwise JWKS is used
    supabase_jwt_audience: str = "authenticated"

    # Demo sandbox for judges / first-time visitors
    demo_enabled: bool = True
    demo_ttl_hours: int = 48

    # LLM explanation layer (optional — every feature has a deterministic fallback)
    anthropic_api_key: str | None = None
    llm_enabled: bool = True
    llm_model: str = "claude-opus-5-5"
    llm_effort: str = "low"
    llm_timeout_seconds: float = 30.0

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url)

    @property
    def llm_available(self) -> bool:
        return self.llm_enabled and bool(self.anthropic_api_key)

    def validate_for_production(self) -> None:
        if self.is_production and self.jwt_secret == DEV_JWT_SECRET:
            raise RuntimeError("JWT_SECRET must be set to a strong random value in production.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_for_production()
    return settings


def local_now() -> datetime:
    """Current Asia/Dhaka wall-clock time as a naive datetime (matches stored expense times)."""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None, microsecond=0)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
