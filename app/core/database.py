"""
database.py — Async SQLAlchemy Engine & Session
================================================
Creates the async database engine and session factory.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings
from app.core.logger import logger


class Base(DeclarativeBase):
    pass


engine: AsyncEngine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=False,  # keep terminal clean; do not print SQL queries
    pool_size=10,
    max_overflow=20, #This means if the 10 normal connections are already busy, SQLAlchemy can temporarily create 20 extra connections. pool_size + max_overflow = 10 + 20= 30
    pool_pre_ping=True,   #Before using a DB connection, check if it is still working. If not working, reconnect safely.
)


AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,  #The _ is added because class is a reserved keyword in Python, so SQLAlchemy uses class_ as a safe parameter name.
    expire_on_commit=False,  #If expire_on_commit=True, SQLAlchemy may expire the object after commit and try to reload it from DB again later.
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:    #because AsyncSessionLocal() gives an async session.
        try:
            yield session
        except Exception as exc:
            logger.error(f"Database error: {exc}")
            await session.rollback()
            raise