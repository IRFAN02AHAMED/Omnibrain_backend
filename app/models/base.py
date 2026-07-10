"""
base.py — Reusable SQLAlchemy Mixins
=====================================
Provides common column mixins that are inherited by OmniBrain models.

Mixins:
  - TimestampMixin: created_at, updated_at
  - AuditMixin:     created_by, updated_by
  - SoftDeleteMixin: is_active (default True)

Usage:
    class Document(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
        __tablename__ = "documents"
        ...
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """
    Adds created_at and updated_at columns.
    created_at is set once on creation.
    updated_at is updated every time the row is modified.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AuditMixin:
    """
    Adds created_by and updated_by columns.
    These store the user ID of who created/modified the record.
    Nullable because system-created records may not have a user.
    """

    created_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    updated_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )


class SoftDeleteMixin:
    """
    Adds is_active column for soft delete.
    Records are never physically deleted — is_active is set to False.
    All queries should filter by is_active=True by default.
    """

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
