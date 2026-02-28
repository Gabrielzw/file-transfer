from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    FILE_PATH_MAX_LENGTH,
    FILENAME_MAX_LENGTH,
    MIME_TYPE_MAX_LENGTH,
    REMARK_MAX_LENGTH,
    UUID_STR_LENGTH,
)
from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(UUID_STR_LENGTH), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(FILENAME_MAX_LENGTH))
    stored_name: Mapped[str] = mapped_column(String(FILENAME_MAX_LENGTH))
    file_path: Mapped[str] = mapped_column(String(FILE_PATH_MAX_LENGTH))
    file_size: Mapped[int] = mapped_column(BigInteger)
    mime_type: Mapped[str] = mapped_column(String(MIME_TYPE_MAX_LENGTH))
    remark: Mapped[str | None] = mapped_column(String(REMARK_MAX_LENGTH), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
    )

    share_links: Mapped[list["ShareLink"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
    )
