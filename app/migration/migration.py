"""
migration.py — Automatic Database Migration
============================================
Runs at application startup via FastAPI lifespan.
Creates all tables defined in the SQLAlchemy models if they don't exist.

This is a "create if not exists" migration approach — safe to run every startup.
For production with schema changes, use Alembic instead.
"""

from sqlalchemy import text

from app.core.database import Base, engine
from app.core.logger import logger

from app.models import (  # noqa: F401
    User,
    ConnectedAccount,
    Document,
    DocumentChunk,
    ChatSession,
    ChatMessage,
    SessionDocument,
    SessionDocumentChunk,
    SyncLog,
)

async def run_migrations() -> None:
    logger.info("[Migration] Starting database setup...")

    try:
        async with engine.begin() as conn:
            # Must create pgvector extension first
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

        logger.info("[Migration] Database setup completed successfully.")

    except Exception as exc:
        logger.error(f"[Migration] Database setup failed: {exc}", exc_info=True)
        raise