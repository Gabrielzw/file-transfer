from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ShareSummary(BaseModel):
    share_code: str
    expire_at: datetime | None
    max_downloads: int | None
    download_count: int
    need_password: bool
    share_url: str


class FileItem(BaseModel):
    id: str
    filename: str
    size: int
    mime_type: str
    remark: str | None
    created_at: datetime
    active_share: ShareSummary | None


class FileListResponse(BaseModel):
    total: int
    list: list[FileItem]


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int


class FileDownloadTokenResponse(BaseModel):
    download_token: str
    expires_in: int
