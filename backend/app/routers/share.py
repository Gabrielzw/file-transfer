from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core.security import (
    InvalidTokenError,
    assert_download_token,
    decode_token,
)
from app.models import File
from app.routers.deps import DbDep, SettingsDep, StorageDep
from app.schemas.share import ShareInfoResponse, VerifyShareRequest, VerifyShareResponse
from app.services import shares_service
from app.services.errors import (
    ShareDownloadLimitReachedError,
    ShareLinkExpiredError,
    ShareLinkInactiveError,
    ShareLinkNotFoundError,
    SharePasswordInvalidError,
)


router = APIRouter()


def _to_410() -> HTTPException:
    return HTTPException(status_code=status.HTTP_410_GONE, detail="链接已失效")


@router.get("/share/{share_code}", response_model=ShareInfoResponse)
def get_share_info(db: DbDep, share_code: str) -> ShareInfoResponse:
    try:
        link = shares_service.require_active_share_link(db=db, share_code=share_code)
    except (ShareLinkExpiredError, ShareLinkInactiveError, ShareDownloadLimitReachedError):
        raise _to_410()
    except ShareLinkNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="链接不存在")

    file = db.get(File, link.file_id)
    if file is None or file.is_deleted:
        raise _to_410()

    return ShareInfoResponse(
        filename=file.original_name,
        size=file.file_size,
        need_password=link.password_hash is not None,
    )


@router.post("/share/{share_code}/verify", response_model=VerifyShareResponse)
def verify_share(
    db: DbDep,
    settings: SettingsDep,
    share_code: str,
    body: VerifyShareRequest,
) -> VerifyShareResponse:
    try:
        link = shares_service.require_active_share_link(db=db, share_code=share_code)
        shares_service.verify_share_password_or_raise(link=link, password=body.password)
    except SharePasswordInvalidError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="提取码错误")
    except (ShareLinkExpiredError, ShareLinkInactiveError, ShareDownloadLimitReachedError):
        raise _to_410()
    except ShareLinkNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="链接不存在")

    token = shares_service.create_download_token(
        jwt_secret=settings.jwt_secret.get_secret_value(),
        share_code=share_code,
        expires_in_seconds=settings.download_token_expires_seconds,
    )
    return VerifyShareResponse(download_token=token, expires_in=settings.download_token_expires_seconds)


@router.get("/share/{share_code}/download")
def download(
    db: DbDep,
    storage: StorageDep,
    settings: SettingsDep,
    share_code: str,
    token: str = Query(min_length=1),
) -> FileResponse:
    try:
        payload = decode_token(secret=settings.jwt_secret.get_secret_value(), token=token)
        assert_download_token(payload=payload)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="下载凭证无效")

    if payload.sub != share_code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="下载凭证无效")

    token_jti = payload.extra.get("jti")
    if not isinstance(token_jti, str) or token_jti.strip() == "":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="下载凭证无效")

    try:
        link = shares_service.require_active_share_link(db=db, share_code=share_code)
    except (ShareLinkExpiredError, ShareLinkInactiveError, ShareDownloadLimitReachedError):
        try:
            link = shares_service.get_share_link(db=db, share_code=share_code)
        except ShareLinkNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="链接不存在")

        if not shares_service.is_download_token_used(db=db, share_id=link.id, token_jti=token_jti):
            raise _to_410()
    except ShareLinkNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="链接不存在")

    file = db.get(File, link.file_id)
    if file is None or file.is_deleted:
        raise _to_410()

    abs_path = storage.resolve_path(relative_path=file.file_path)
    if not Path(abs_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    shares_service.increase_download_count(db=db, share_id=link.id, token_jti=token_jti)

    return FileResponse(
        path=abs_path,
        filename=file.original_name,
        media_type=file.mime_type or "application/octet-stream",
    )
