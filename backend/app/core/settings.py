from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    DEFAULT_ADMIN_TOKEN_EXPIRES_SECONDS,
    DEFAULT_DOWNLOAD_TOKEN_EXPIRES_SECONDS,
    DEFAULT_MAX_UPLOAD_BYTES,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    jwt_secret: SecretStr = Field(min_length=1)
    admin_username: str = Field(min_length=1)
    admin_password: SecretStr = Field(min_length=1)

    public_base_url: str = Field(default="")
    cors_origins: str = Field(default="")

    db_path: str = Field(default="./data/app.db")
    storage_dir: str = Field(default="../uploads")
    max_upload_bytes: int = Field(default=DEFAULT_MAX_UPLOAD_BYTES, gt=0)

    admin_token_expires_seconds: int = Field(
        default=DEFAULT_ADMIN_TOKEN_EXPIRES_SECONDS,
        gt=0,
    )
    download_token_expires_seconds: int = Field(
        default=DEFAULT_DOWNLOAD_TOKEN_EXPIRES_SECONDS,
        gt=0,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
