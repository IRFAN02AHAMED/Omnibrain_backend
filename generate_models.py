import os

models_dir = "app/models"
os.makedirs(models_dir, exist_ok=True)

models = {
    "user.py": """from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class User(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_picture: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="google", nullable=False)

    connected_accounts = relationship("ConnectedAccount", back_populates="user", lazy="selectin")
    documents = relationship("Document", back_populates="owner", lazy="selectin")
    chat_sessions = relationship("ChatSession", back_populates="user", lazy="selectin")
    sync_logs = relationship("SyncLog", back_populates="user", lazy="selectin")
""",
    "connected_account.py": """from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class ConnectedAccount(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "connected_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), default="google", nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_picture: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    token_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    token_expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scopes: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )

    user = relationship("User", back_populates="connected_accounts")
""",
    "document.py": """from datetime import datetime
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
""",
    "document_chunk.py": """from sqlalchemy import Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class DocumentChunk(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(768), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    document = relationship("Document", back_populates="chunks")
""",
    "chat_session.py": """from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class ChatSession(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", lazy="selectin", cascade="all, delete-orphan")
    session_documents = relationship("SessionDocument", back_populates="session", lazy="selectin", cascade="all, delete-orphan")
""",
    "chat_message.py": """from sqlalchemy import Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class ChatMessage(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False) # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_chunks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    used_global_documents: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_session_documents: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session = relationship("ChatSession", back_populates="messages")
""",
    "session_document.py": """from datetime import datetime
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
""",
    "session_document_chunk.py": """from sqlalchemy import Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin

class SessionDocumentChunk(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "session_document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("session_documents.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(768), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    session_document = relationship("SessionDocument", back_populates="chunks")
""",
    "sync_log.py": """from datetime import datetime
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
""",
    "__init__.py": """from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.session_document import SessionDocument
from app.models.session_document_chunk import SessionDocumentChunk
from app.models.sync_log import SyncLog

__all__ = [
    "User",
    "ConnectedAccount",
    "Document",
    "DocumentChunk",
    "ChatSession",
    "ChatMessage",
    "SessionDocument",
    "SessionDocumentChunk",
    "SyncLog",
]
"""
}

for name, content in models.items():
    with open(f"{models_dir}/{name}", "w") as f:
        f.write(content)
print("Models generated.")
