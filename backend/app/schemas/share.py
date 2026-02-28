from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


_PASSWORD_PATTERN = re.compile(r"^[A-Za-z0-9]{4,8}$")


class CreateShareRequest(BaseModel):
    password: str | None = Field(default=None)
    expire_hours: int | None = Field(default=None, gt=0)
    max_downloads: int | None = Field(default=None, gt=0)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return None

        password = value.strip()
        if password == "":
            return None

        if not _PASSWORD_PATTERN.fullmatch(password):
            raise ValueError("提取码需为4~8位字母或数字")
        return password


class CreateShareResponse(BaseModel):
    share_code: str
    share_url: str
    expire_at: datetime | None


class ShareInfoResponse(BaseModel):
    filename: str
    size: int
    need_password: bool


class VerifyShareRequest(BaseModel):
    password: str | None = Field(default=None)


class VerifyShareResponse(BaseModel):
    download_token: str
    expires_in: int
