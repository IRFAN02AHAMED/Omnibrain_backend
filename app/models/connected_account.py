from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, AuditMixin, SoftDeleteMixin


class ConnectedAccount(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Stores one OAuth connection per user and provider.

    provider examples:
    - google
    - jira
    - github

    One row per user per provider.
    Reconnecting updates the same row.
    """

    __tablename__ = "connected_accounts"

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Provider profile/account details
    provider_account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_picture: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # OAuth tokens
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Store provider-specific data here:
    # Jira: cloud_id, site_url, site_name
    # GitHub: github_username
    # Google: Drive folder IDs
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    is_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="connected_accounts")