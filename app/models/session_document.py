from datetime import datetime
from sqlalchemy import Integer, String, BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class SessionDocument(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "session_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    drive_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    drive_web_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    drive_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    folder_path: Mapped[str | None] = mapped_column(String(500), default="OmniBrain AI/Chat Documents", nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint('owner_id', 'session_id', 'drive_file_id', name='uq_owner_session_drive_file'),
    )

    session = relationship("ChatSession", back_populates="session_documents")
    chunks = relationship("SessionDocumentChunk", back_populates="session_document", lazy="selectin", cascade="all, delete-orphan")
