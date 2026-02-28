from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import UUID_STR_LENGTH
from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ShareDownloadToken(Base):
    __tablename__ = "share_download_tokens"

    jti: Mapped[str] = mapped_column(String(UUID_STR_LENGTH), primary_key=True)
    share_id: Mapped[str] = mapped_column(
        String(UUID_STR_LENGTH),
        ForeignKey("share_links.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

