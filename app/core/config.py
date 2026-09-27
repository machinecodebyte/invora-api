import json
import re
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = Field(..., min_length=1)
    APP_TAGLINE: str = "Predict - Optimize - Replenish"
    APP_ENV: str = Field(..., min_length=1)
    DEBUG: bool
    API_V1_PREFIX: str = Field(..., min_length=1)
    API_HOST: str = Field(default="127.0.0.1", min_length=1)
    API_PORT: int = Field(default=8000, ge=1, le=65535)
    API_PORT_FALLBACK_ENABLED: bool = False
    DATABASE_URL: str = Field(..., min_length=1)
    REDIS_URL: str = Field(..., min_length=1)
    WORKER_ENABLED: bool = True
    RQ_DEFAULT_QUEUE: str = Field(default="invora-default", min_length=1)
    RQ_FORECAST_QUEUE: str = Field(default="invora-forecasting", min_length=1)
    RQ_JOB_TIMEOUT_SECONDS: int = Field(default=1800, gt=0)
    RQ_MAX_RETRIES: int = Field(default=3, ge=0)
    RQ_RETRY_INTERVAL_SECONDS: int = Field(default=30, ge=0)
    RQ_RESULT_TTL_SECONDS: int = Field(default=86400, ge=0)
    RQ_FAILURE_TTL_SECONDS: int = Field(default=604800, ge=0)
    RQ_WORKER_NAME_PREFIX: str = Field(default="invora-worker", min_length=1)
    RQ_WORKER_TTL_SECONDS: int = Field(default=60, gt=15)
    CORS_ORIGINS: str = Field(..., min_length=1)
    LOG_LEVEL: str = Field(..., min_length=1)
    JWT_SECRET_KEY: SecretStr = Field(..., min_length=16)
    AUTH_RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=900, ge=1, le=86400)
    AUTH_LOGIN_MAX_ATTEMPTS_PER_IP: int = Field(default=20, ge=1, le=10000)
    AUTH_LOGIN_MAX_ATTEMPTS_PER_ACCOUNT: int = Field(default=10, ge=1, le=10000)
    AUTH_REGISTER_MAX_ATTEMPTS_PER_IP: int = Field(default=5, ge=1, le=10000)
    AUTH_REFRESH_MAX_ATTEMPTS_PER_IP: int = Field(default=30, ge=1, le=10000)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(..., gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, gt=0)
    REFRESH_COOKIE_NAME: str = Field(default="invora_refresh_token", min_length=1)
    REFRESH_COOKIE_SECURE: bool | None = None
    REFRESH_COOKIE_SAMESITE: str = Field(default="lax", min_length=1)
    REFRESH_COOKIE_DOMAIN: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("API_V1_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            msg = "API_V1_PREFIX must start with /"
            raise ValueError(msg)
        return value.rstrip("/") or "/"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        normalized = str(value).strip()
        prefixes = {
            "postgres://": "postgresql+asyncpg://",
            "postgres+asyncpg://": "postgresql+asyncpg://",
            "postgresql://": "postgresql+asyncpg://",
        }
        for source_prefix, target_prefix in prefixes.items():
            if normalized.startswith(source_prefix):
                normalized = target_prefix + normalized.removeprefix(source_prefix)
                break

        if not normalized.startswith("postgresql+asyncpg://"):
            msg = "DATABASE_URL must use the postgresql+asyncpg:// dialect"
            raise ValueError(msg)
        return normalized

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("redis://", "rediss://")):
            msg = "REDIS_URL must use the redis:// or rediss:// scheme"
            raise ValueError(msg)
        return normalized

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_value(cls, value: bool | str) -> bool | str:
        if not isinstance(value, str):
            return value

        normalized = value.strip().lower()
        aliases = {
            "development": True,
            "dev": True,
            "production": False,
            "prod": False,
            "release": False,
        }
        return aliases.get(normalized, value)

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            msg = f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}"
            raise ValueError(msg)
        return normalized

    @field_validator("REFRESH_COOKIE_NAME")
    @classmethod
    def validate_refresh_cookie_name(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[!#$%&'*+.^_|~0-9A-Za-z-]+", normalized):
            msg = "REFRESH_COOKIE_NAME must be a valid cookie name"
            raise ValueError(msg)
        return normalized

    @field_validator("REFRESH_COOKIE_SAMESITE")
    @classmethod
    def validate_refresh_cookie_samesite(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            msg = "REFRESH_COOKIE_SAMESITE must be one of: lax, strict, none"
            raise ValueError(msg)
        return normalized

    @field_validator("REFRESH_COOKIE_DOMAIN", mode="before")
    @classmethod
    def normalize_refresh_cookie_domain(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_production_debug(self) -> "Settings":
        is_production = self.APP_ENV.strip().lower() in {"prod", "production"}
        if is_production and self.DEBUG:
            msg = "DEBUG must be false when APP_ENV is production"
            raise ValueError(msg)
        if is_production and self.REFRESH_COOKIE_SECURE is False:
            msg = "REFRESH_COOKIE_SECURE must be true when APP_ENV is production"
            raise ValueError(msg)
        if self.API_PORT_FALLBACK_ENABLED and self.APP_ENV.strip().lower() not in {
            "dev",
            "development",
            "local",
        }:
            msg = "API_PORT_FALLBACK_ENABLED is allowed only in local development"
            raise ValueError(msg)
        if is_production and not self.AUTH_RATE_LIMIT_ENABLED:
            msg = "AUTH_RATE_LIMIT_ENABLED must be true when APP_ENV is production"
            raise ValueError(msg)
        if self.REFRESH_COOKIE_SAMESITE == "none" and not self.refresh_cookie_secure:
            msg = "REFRESH_COOKIE_SAMESITE=none requires REFRESH_COOKIE_SECURE=true"
            raise ValueError(msg)
        return self

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        raw_value = value.strip()
        if raw_value == "*":
            msg = "CORS_ORIGINS cannot use wildcard origins with credentials"
            raise ValueError(msg)

        if raw_value.startswith("["):
            try:
                parsed: Any = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                msg = "CORS_ORIGINS must be a comma-separated string or JSON list"
                raise ValueError(msg) from exc

            if not isinstance(parsed, list) or not all(
                isinstance(item, str) and item.strip() for item in parsed
            ):
                msg = "CORS_ORIGINS JSON value must be a non-empty list of strings"
                raise ValueError(msg)
            if "*" in {origin.strip() for origin in parsed}:
                msg = "CORS_ORIGINS cannot use wildcard origins with credentials"
                raise ValueError(msg)
            return raw_value

        origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
        if not origins:
            msg = "CORS_ORIGINS must include at least one origin"
            raise ValueError(msg)
        if "*" in origins:
            msg = "CORS_ORIGINS cannot use wildcard origins with credentials"
            raise ValueError(msg)
        return raw_value

    @property
    def cors_origin_list(self) -> list[str]:
        raw_value = self.CORS_ORIGINS.strip()
        if raw_value.startswith("["):
            try:
                parsed: Any = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                msg = "CORS_ORIGINS must be a comma-separated string or JSON list"
                raise ValueError(msg) from exc

            if not isinstance(parsed, list) or not all(
                isinstance(item, str) for item in parsed
            ):
                msg = "CORS_ORIGINS JSON value must be a list of strings"
                raise ValueError(msg)

            return [origin.strip() for origin in parsed if origin.strip()]

        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    @property
    def database_host(self) -> str:
        return urlsplit(self.DATABASE_URL).hostname or "unknown"

    @property
    def database_name(self) -> str:
        database_name = urlsplit(self.DATABASE_URL).path.lstrip("/")
        return database_name or "unknown"

    @staticmethod
    def _asyncpg_connection_configuration(
        database_url: str,
    ) -> tuple[str, dict[str, bool | str]]:
        parsed_url = urlsplit(database_url)
        query_items = parse_qsl(parsed_url.query, keep_blank_values=True)
        asyncpg_query_items = [
            (key, value) for key, value in query_items if key != "sslmode"
        ]
        sslmode = next((value for key, value in query_items if key == "sslmode"), None)
        connect_args: dict[str, bool | str] = {}
        if sslmode is not None:
            # asyncpg treats the string "verify-full" as a libpq compatibility
            # mode and looks for ~/.postgresql/root.crt. True instead creates a
            # default system-trust SSL context with hostname verification.
            connect_args["ssl"] = True if sslmode == "verify-full" else sslmode
        asyncpg_url = urlunsplit(
            parsed_url._replace(query=urlencode(asyncpg_query_items, doseq=True))
        )
        return asyncpg_url, connect_args

    @property
    def asyncpg_database_url(self) -> str:
        """Return DATABASE_URL without libpq-only query parameters."""
        return self._asyncpg_connection_configuration(self.DATABASE_URL)[0]

    @property
    def asyncpg_connect_args(self) -> dict[str, bool | str]:
        """Return asyncpg-compatible connection arguments from DATABASE_URL."""
        return self._asyncpg_connection_configuration(self.DATABASE_URL)[1]

    @property
    def migration_database_url(self) -> str:
        """Use Prisma Postgres' direct endpoint for Alembic administrative work."""
        parsed_url = urlsplit(self.DATABASE_URL)
        if parsed_url.hostname != "pooled.db.prisma.io":
            return self.DATABASE_URL

        credentials, separator, _ = parsed_url.netloc.rpartition("@")
        if not separator:
            return self.DATABASE_URL

        direct_netloc = f"{credentials}@db.prisma.io"
        if parsed_url.port is not None:
            direct_netloc = f"{direct_netloc}:{parsed_url.port}"
        return urlunsplit(parsed_url._replace(netloc=direct_netloc))

    @property
    def migration_asyncpg_database_url(self) -> str:
        return self._asyncpg_connection_configuration(self.migration_database_url)[0]

    @property
    def migration_asyncpg_connect_args(self) -> dict[str, bool | str]:
        return self._asyncpg_connection_configuration(self.migration_database_url)[1]

    @property
    def redis_host(self) -> str:
        return urlsplit(self.REDIS_URL).hostname or "unknown"

    @property
    def startup_log_context(self) -> dict[str, str | int | bool]:
        return {
            "app_env": self.APP_ENV,
            "debug": self.DEBUG,
            "database_host": self.database_host,
            "database_name": self.database_name,
            "redis_host": self.redis_host,
            "api_host": self.API_HOST,
            "api_port": self.API_PORT,
            "worker_enabled": self.WORKER_ENABLED,
        }

    @property
    def refresh_cookie_secure(self) -> bool:
        if self.APP_ENV.strip().lower() in {"prod", "production"}:
            return True
        return self.REFRESH_COOKIE_SECURE is True

    @property
    def refresh_cookie_path(self) -> str:
        return f"{self.API_V1_PREFIX}/auth"

    @property
    def refresh_cookie_max_age_seconds(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
