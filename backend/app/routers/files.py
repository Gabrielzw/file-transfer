from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.constants import BYTES_PER_MEBIBYTE
from app.core.security import InvalidTokenError, assert_download_token, decode_token
from app.routers.deps import AdminDep, DbDep, SettingsDep, StorageDep
from app.schemas.files import (
    FileDownloadTokenResponse,
    FileItem,
    FileListResponse,
    ShareSummary,
    UploadResponse,
)
from app.schemas.share import CreateShareRequest, CreateShareResponse
from app.services import files_service, shares_service
from app.services.errors import FileNotFoundError
from app.storage import FileTooLargeError


router = APIRouter()


def _build_share_url(*, base: str, share_code: str) -> str:
    path = f"/s/{share_code}"
    if not base:
        return path
    return f"{base.rstrip('/')}{path}"


@router.post("/files/upload", response_model=UploadResponse)
def upload_file(
    _: AdminDep,
    db: DbDep,
    storage: StorageDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    remark: str | None = Form(default=None),
) -> UploadResponse:
    try:
        created = files_service.upload_file(
            db=db,
            storage=storage,
            source=file.file,
            original_filename=file.filename or "unnamed",
            mime_type=file.content_type or "application/octet-stream",
            remark=remark,
            max_upload_bytes=settings.max_upload_bytes,
        )
    except FileTooLargeError:
        limit_mb = settings.max_upload_bytes // BYTES_PER_MEBIBYTE
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件超过最大限制 {limit_mb}MB",
        )

    return UploadResponse(
        file_id=created.id,
        filename=created.original_name,
        size=created.file_size,
    )


@router.get("/files", response_model=FileListResponse)
def list_files(
    _: AdminDep,
    db: DbDep,
    settings: SettingsDep,
    page: int = Query(default=1, gt=0),
    size: int = Query(default=20, gt=0),
    keyword: str | None = Query(default=None),
) -> FileListResponse:
    total, items = files_service.list_files(db=db, page=page, size=size, keyword=keyword)

    out: list[FileItem] = []
    for item in items:
        share = item.active_share
        share_out = None
        if share is not None:
            share_out = ShareSummary(
                share_code=share.share_code,
                expire_at=share.expire_at,
                max_downloads=share.max_downloads,
                download_count=share.download_count,
                need_password=share.password_hash is not None,
                share_url=_build_share_url(
                    base=settings.public_base_url,
                    share_code=share.share_code,
                ),
            )

        out.append(
            FileItem(
                id=item.file.id,
                filename=item.file.original_name,
                size=item.file.file_size,
                mime_type=item.file.mime_type,
                remark=item.file.remark,
                created_at=item.file.created_at,
                active_share=share_out,
            )
        )

    return FileListResponse(total=total, list=out)


@router.delete("/files/{file_id}")
def delete_file(_: AdminDep, db: DbDep, storage: StorageDep, file_id: str) -> dict[str, bool]:
    try:
        files_service.delete_file(db=db, storage=storage, file_id=file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return {"success": True}


@router.post("/files/{file_id}/share", response_model=CreateShareResponse)
def create_share_link(
    _: AdminDep,
    db: DbDep,
    settings: SettingsDep,
    file_id: str,
    body: CreateShareRequest,
) -> CreateShareResponse:
    try:
        link = shares_service.create_share_link(
            db=db,
            file_id=file_id,
            params=shares_service.ShareCreateParams(
                password=body.password,
                expire_hours=body.expire_hours,
                max_downloads=body.max_downloads,
            ),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    return CreateShareResponse(
        share_code=link.share_code,
        share_url=_build_share_url(base=settings.public_base_url, share_code=link.share_code),
        expire_at=link.expire_at,
    )


@router.post("/files/{file_id}/download-token", response_model=FileDownloadTokenResponse)
def create_download_token(
    _: AdminDep,
    db: DbDep,
    settings: SettingsDep,
    file_id: str,
) -> FileDownloadTokenResponse:
    try:
        files_service.require_file(db=db, file_id=file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    token = files_service.create_file_download_token(
        jwt_secret=settings.jwt_secret.get_secret_value(),
        file_id=file_id,
        expires_in_seconds=settings.download_token_expires_seconds,
    )
    return FileDownloadTokenResponse(
        download_token=token,
        expires_in=settings.download_token_expires_seconds,
    )


@router.get("/files/{file_id}/download")
def download_file(
    db: DbDep,
    storage: StorageDep,
    settings: SettingsDep,
    file_id: str,
    token: str = Query(min_length=1),
) -> FileResponse:
    try:
        payload = decode_token(secret=settings.jwt_secret.get_secret_value(), token=token)
        assert_download_token(payload=payload)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="下载凭证无效")

    if payload.sub != file_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="下载凭证无效")

    try:
        file = files_service.require_file(db=db, file_id=file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    abs_path = storage.resolve_path(relative_path=file.file_path)
    if not Path(abs_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    return FileResponse(
        path=abs_path,
        filename=file.original_name,
        media_type=file.mime_type or "application/octet-stream",
    )
