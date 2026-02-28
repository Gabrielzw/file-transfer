from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.constants import DOWNLOAD_TOKEN_TYPE
from app.core.security import create_token
from app.models import File, ShareLink
from app.services.errors import FileNotFoundError
from app.storage import Storage, StorageFileNotFoundError


@dataclass(frozen=True)
class FileWithShare:
    file: File
    active_share: ShareLink | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def require_file(*, db: Session, file_id: str) -> File:
    file = db.get(File, file_id)
    if file is None or file.is_deleted:
        raise FileNotFoundError(file_id)
    return file


def create_file_download_token(*, jwt_secret: str, file_id: str, expires_in_seconds: int) -> str:
    return create_token(
        secret=jwt_secret,
        token_type=DOWNLOAD_TOKEN_TYPE,
        subject=file_id,
        expires_in_seconds=expires_in_seconds,
    )


def deactivate_invalid_shares(*, db: Session) -> None:
    now = _utc_now()
    stmt = (
        update(ShareLink)
        .where(ShareLink.is_active.is_(True))
        .where(
            or_(
                and_(ShareLink.expire_at.is_not(None), ShareLink.expire_at <= now),
                and_(
                    ShareLink.max_downloads.is_not(None),
                    ShareLink.download_count >= ShareLink.max_downloads,
                ),
            )
        )
        .values(is_active=False)
    )
    db.execute(stmt)
    db.commit()


def upload_file(
    *,
    db: Session,
    storage: Storage,
    source: BinaryIO,
    original_filename: str,
    mime_type: str,
    remark: str | None,
    max_upload_bytes: int,
) -> File:
    safe_name = os.path.basename(original_filename)
    stored = storage.save(
        source=source,
        original_filename=safe_name,
        max_bytes=max_upload_bytes,
    )

    file = File(
        id=str(uuid4()),
        original_name=safe_name,
        stored_name=stored.stored_name,
        file_path=stored.relative_path,
        file_size=stored.size_bytes,
        mime_type=mime_type,
        remark=remark,
    )
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


def list_files(
    *,
    db: Session,
    page: int,
    size: int,
    keyword: str | None,
) -> tuple[int, list[FileWithShare]]:
    deactivate_invalid_shares(db=db)

    file_filters = [File.is_deleted.is_(False)]
    if keyword:
        like = f"%{keyword}%"
        file_filters.append(or_(File.original_name.like(like), File.remark.like(like)))

    total = db.scalar(select(func.count()).select_from(File).where(and_(*file_filters)))
    offset = (page - 1) * size

    stmt = (
        select(File, ShareLink)
        .outerjoin(
            ShareLink,
            and_(ShareLink.file_id == File.id, ShareLink.is_active.is_(True)),
        )
        .where(and_(*file_filters))
        .order_by(File.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    rows = db.execute(stmt).all()
    items = [FileWithShare(file=row[0], active_share=row[1]) for row in rows]
    return (int(total or 0), items)


def delete_file(*, db: Session, storage: Storage, file_id: str) -> None:
    file = require_file(db=db, file_id=file_id)

    try:
        storage.delete(relative_path=file.file_path)
    except StorageFileNotFoundError as exc:
        raise FileNotFoundError(str(exc)) from exc

    db.execute(
        update(ShareLink)
        .where(ShareLink.file_id == file_id)
        .values(is_active=False)
    )
    file.is_deleted = True
    db.commit()
