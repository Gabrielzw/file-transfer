from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.constants import DOWNLOAD_TOKEN_TYPE, SHARE_CODE_LENGTH, SHARE_CODE_MAX_RETRIES
from app.core.security import create_token, hash_password, verify_password
from app.models import File, ShareDownloadToken, ShareLink
from app.services.errors import (
    FileNotFoundError,
    ShareDownloadLimitReachedError,
    ShareLinkExpiredError,
    ShareLinkInactiveError,
    ShareLinkNotFoundError,
    SharePasswordInvalidError,
)


SHARE_CODE_ALPHABET = string.ascii_letters + string.digits


@dataclass(frozen=True)
class ShareCreateParams:
    password: str | None
    expire_hours: int | None
    max_downloads: int | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_aware(value: datetime) -> datetime:
    tzinfo = value.tzinfo
    if tzinfo is None or tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _generate_share_code() -> str:
    return "".join(secrets.choice(SHARE_CODE_ALPHABET) for _ in range(SHARE_CODE_LENGTH))


def _require_file(*, db: Session, file_id: str) -> File:
    file = db.get(File, file_id)
    if file is None or file.is_deleted:
        raise FileNotFoundError(file_id)
    return file


def _deactivate_file_shares(*, db: Session, file_id: str) -> None:
    stmt = (
        update(ShareLink)
        .where(and_(ShareLink.file_id == file_id, ShareLink.is_active.is_(True)))
        .values(is_active=False)
    )
    db.execute(stmt)


def create_share_link(*, db: Session, file_id: str, params: ShareCreateParams) -> ShareLink:
    _require_file(db=db, file_id=file_id)
    _deactivate_file_shares(db=db, file_id=file_id)

    password_hash = hash_password(password=params.password) if params.password else None
    expire_at = (
        _utc_now() + timedelta(hours=params.expire_hours) if params.expire_hours else None
    )

    share_code = None
    for _ in range(SHARE_CODE_MAX_RETRIES):
        candidate = _generate_share_code()
        exists = db.scalar(select(ShareLink.id).where(ShareLink.share_code == candidate))
        if exists is None:
            share_code = candidate
            break
    if share_code is None:
        raise RuntimeError("Failed to generate unique share_code")

    link = ShareLink(
        id=str(uuid4()),
        file_id=file_id,
        share_code=share_code,
        password_hash=password_hash,
        expire_at=expire_at,
        max_downloads=params.max_downloads,
        download_count=0,
        is_active=True,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def get_share_link(*, db: Session, share_code: str) -> ShareLink:
    link = db.scalar(select(ShareLink).where(ShareLink.share_code == share_code))
    if link is None:
        raise ShareLinkNotFoundError(share_code)
    return link


def require_active_share_link(*, db: Session, share_code: str) -> ShareLink:
    link = get_share_link(db=db, share_code=share_code)
    if not link.is_active:
        raise ShareLinkInactiveError(share_code)

    now = _utc_now()
    if link.expire_at and _as_utc_aware(link.expire_at) <= now:
        db.execute(update(ShareLink).where(ShareLink.id == link.id).values(is_active=False))
        db.commit()
        raise ShareLinkExpiredError(share_code)

    if link.max_downloads is not None and link.download_count >= link.max_downloads:
        db.execute(update(ShareLink).where(ShareLink.id == link.id).values(is_active=False))
        db.commit()
        raise ShareDownloadLimitReachedError(share_code)

    return link


def verify_share_password_or_raise(*, link: ShareLink, password: str | None) -> None:
    if link.password_hash is None:
        return
    if not password or not verify_password(password=password, password_hash=link.password_hash):
        raise SharePasswordInvalidError()


def create_download_token(
    *,
    jwt_secret: str,
    share_code: str,
    expires_in_seconds: int,
) -> str:
    jti = str(uuid4())
    return create_token(
        secret=jwt_secret,
        token_type=DOWNLOAD_TOKEN_TYPE,
        subject=share_code,
        expires_in_seconds=expires_in_seconds,
        extra={"jti": jti},
    )


def is_download_token_used(*, db: Session, share_id: str, token_jti: str) -> bool:
    stmt = (
        select(ShareDownloadToken.jti)
        .where(ShareDownloadToken.jti == token_jti)
        .where(ShareDownloadToken.share_id == share_id)
    )
    return db.scalar(stmt) is not None


def _try_register_download_token(*, db: Session, share_id: str, token_jti: str) -> bool:
    stmt = sqlite_insert(ShareDownloadToken).values(
        jti=token_jti,
        share_id=share_id,
        created_at=_utc_now(),
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=[ShareDownloadToken.jti])
    result = db.execute(stmt)
    return bool(result.rowcount)


def increase_download_count(*, db: Session, share_id: str, token_jti: str) -> None:
    if not _try_register_download_token(db=db, share_id=share_id, token_jti=token_jti):
        return

    link = db.get(ShareLink, share_id)
    if link is None:
        raise ShareLinkNotFoundError(share_id)

    if link.max_downloads is not None and link.download_count >= link.max_downloads:
        db.execute(update(ShareLink).where(ShareLink.id == link.id).values(is_active=False))
        db.commit()
        raise ShareDownloadLimitReachedError(link.share_code)

    new_count = link.download_count + 1
    values: dict[str, object] = {"download_count": new_count}
    if link.max_downloads is not None and new_count >= link.max_downloads:
        values["is_active"] = False

    db.execute(update(ShareLink).where(ShareLink.id == link.id).values(**values))
    db.commit()
