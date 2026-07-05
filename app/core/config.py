import json
from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = Field(..., min_length=1)
    APP_TAGLINE: str = "Predict - Optimize - Replenish"
    APP_ENV: str = Field(..., min_length=1)
    DEBUG: bool
    API_V1_PREFIX: str = Field(..., min_length=1)
    DATABASE_URL: str = Field(..., min_length=1)
    REDIS_URL: str = Field(..., min_length=1)
    CORS_ORIGINS: str = Field(..., min_length=1)
    LOG_LEVEL: str = Field(..., min_length=1)
    JWT_SECRET_KEY: SecretStr = Field(..., min_length=16)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(..., gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, gt=0)

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

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            msg = f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}"
            raise ValueError(msg)
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        raw_value = self.CORS_ORIGINS.strip()
        if raw_value == "*":
            return ["*"]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
