from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    PASSWORD_HASH_MAX_LENGTH,
    SHARE_CODE_LENGTH,
    UUID_STR_LENGTH,
)
from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[str] = mapped_column(String(UUID_STR_LENGTH), primary_key=True)
    file_id: Mapped[str] = mapped_column(
        String(UUID_STR_LENGTH),
        ForeignKey("files.id", ondelete="CASCADE"),
        index=True,
    )
    share_code: Mapped[str] = mapped_column(
        String(SHARE_CODE_LENGTH),
        unique=True,
        index=True,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(PASSWORD_HASH_MAX_LENGTH),
        nullable=True,
    )
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_downloads: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    file: Mapped["File"] = relationship(back_populates="share_links")
