from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class SyncLog(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), default="google_drive", nullable=False)
    sync_type: Mapped[str] = mapped_column(String(50), default="manual_drive_sync", nullable=False)
    folder_path: Mapped[str | None] = mapped_column(String(500), default="OmniBrain AI/Global Documents", nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False) # started, completed, failed
    files_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sync_logs")
