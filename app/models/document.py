from datetime import datetime
from sqlalchemy import Integer, String, BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class Document(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    drive_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    drive_web_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    drive_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    folder_path: Mapped[str | None] = mapped_column(String(500), default="OmniBrain AI/Global Documents", nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('owner_id', 'drive_file_id', name='uq_owner_drive_file'),
    )

    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", lazy="selectin", cascade="all, delete-orphan")
