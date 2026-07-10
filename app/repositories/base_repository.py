"""
base_repository.py — Generic Base Repository
=============================================
Provides common CRUD operations that all other repositories inherit.
This avoids repeating the same get/list/create/update/delete code
in every repository file.

PRINCIPLES:
  - Always filter is_active=True
  - Never contain business logic
  - Only use SQLAlchemy ORM queries
  - Always use async/await
"""

from typing import TypeVar, Generic, Type, Optional, List, Any
from uuid import UUID
from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.logger import logger


# T is a placeholder for any SQLAlchemy model class
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Generic async repository providing standard CRUD operations.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(db, User)

    Every method in this class:
      - Is async
      - Filters is_active=True by default
      - Logs what it's doing at DEBUG level
    """

    def __init__(self, db: AsyncSession, model: Type[T]) -> None:
        """
        Args:
            db:    Active async database session (injected by FastAPI).
            model: The SQLAlchemy model class this repository manages.
        """
        self.db    = db
        self.model = model

    # ── READ ──────────────────────────────────────────────────────────────────

    async def get_by_id_int(self, record_id: int) -> Optional[T]:
        """
        Fetches one record by its integer primary key.
        Returns None if the record does not exist or is inactive.

        Args:
            record_id: Integer primary key of the record.

        Returns:
            Model instance or None.
        """
        logger.debug(f"[{self.model.__name__}] get_by_id_int: {record_id}")
        stmt = select(self.model).where(
            self.model.id == record_id,
            self.model.is_active == True,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, record_id: UUID) -> Optional[T]:
        """
        Fetches one record by its UUID primary key.
        Returns None if the record does not exist or is inactive.

        Args:
            record_id: UUID primary key of the record.

        Returns:
            Model instance or None.
        """
        logger.debug(f"[{self.model.__name__}] get_by_id: {record_id}")
        stmt = select(self.model).where(
            self.model.id == record_id,
            self.model.is_active == True,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self) -> List[T]:
        """
        Returns all active records with no filtering or pagination.
        Use list_paginated() for API list endpoints instead.

        Returns:
            List of model instances.
        """
        logger.debug(f"[{self.model.__name__}] get_all")
        stmt = select(self.model).where(self.model.is_active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_paginated(
        self,
        page:       int = 1,
        page_size:  int = 10,
        search_col: Optional[Any] = None,  # pass model column: e.g. User.name
        search_val: Optional[str] = None,
        sort_col:   Optional[Any] = None,
        sort_order: str = "desc",
        extra_filters: Optional[list] = None,
    ) -> tuple[List[T], int]:
        """
        Returns a paginated, optionally searched and sorted list of active records.

        Args:
            page:          Page number (1-indexed).
            page_size:     Number of records per page.
            search_col:    SQLAlchemy column to apply ILIKE search on.
            search_val:    Search string (case-insensitive partial match).
            sort_col:      Column to sort by.
            sort_order:    'asc' or 'desc'.
            extra_filters: Additional SQLAlchemy WHERE conditions.

        Returns:
            Tuple of (list of records, total count).

        Example:
            records, total = await repo.list_paginated(
                page=1, page_size=10,
                search_col=User.name, search_val="irfan",
                sort_col=User.created_at, sort_order="desc"
            )
        """
        logger.debug(f"[{self.model.__name__}] list_paginated page={page} size={page_size}")

        # Build base WHERE conditions
        conditions = [self.model.is_active == True]

        if extra_filters:
            conditions.extend(extra_filters)

        # Add search condition if provided
        if search_col is not None and search_val:
            conditions.append(search_col.ilike(f"%{search_val}%"))

        # Count query — get total matching records
        count_stmt = select(func.count()).select_from(self.model).where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query with sorting and pagination
        data_stmt = select(self.model).where(*conditions)

        if sort_col is not None:
            order_fn = asc if sort_order == "asc" else desc
            data_stmt = data_stmt.order_by(order_fn(sort_col))
        else:
            # Default: newest first
            if hasattr(self.model, "created_at"):
                data_stmt = data_stmt.order_by(desc(self.model.created_at))

        # Apply pagination: OFFSET = (page - 1) * page_size
        offset = (page - 1) * page_size
        data_stmt = data_stmt.offset(offset).limit(page_size)

        data_result = await self.db.execute(data_stmt)
        records = list(data_result.scalars().all())

        return records, total

    # ── CREATE ────────────────────────────────────────────────────────────────

    async def create(self, instance: T) -> T:
        """
        Persists a new model instance to the database.

        Args:
            instance: An already-constructed model object.

        Returns:
            The same instance, now with DB-generated id and timestamps.

        Example:
            user = User(name="Irfan", email="x@x.com", ...)
            saved_user = await repo.create(user)
        """
        logger.debug(f"[{self.model.__name__}] create")
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def create_many(self, instances: List[T]) -> List[T]:
        """
        Persists multiple model instances in one transaction.
        More efficient than calling create() in a loop.

        Args:
            instances: List of model objects.

        Returns:
            The same list, now persisted.
        """
        logger.debug(f"[{self.model.__name__}] create_many count={len(instances)}")
        self.db.add_all(instances)
        await self.db.commit()
        for inst in instances:
            await self.db.refresh(inst)
        return instances

    async def bulk_create(self, instances: List[T]) -> List[T]:
        """
        Alias for create_many to match prompt instructions.
        """
        return await self.create_many(instances)


    # ── UPDATE ────────────────────────────────────────────────────────────────

    async def update(self, instance: T, update_data: dict) -> T:
        """
        Updates only the provided fields on an existing record.

        Args:
            instance:    Existing ORM instance fetched from DB.
            update_data: Dict of {column_name: new_value} pairs.

        Returns:
            Updated ORM instance.

        Example:
            user = await repo.get_by_id(uid)
            updated = await repo.update(user, {"name": "New Name"})
        """
        logger.debug(f"[{self.model.__name__}] update id={instance.id} fields={list(update_data.keys())}")
        for field, value in update_data.items():
            if value is not None:  # Only update fields that were actually provided
                setattr(instance, field, value)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    # ── DELETE (soft) ────────────────────────────────────────────────────────

    async def soft_delete(self, instance: T) -> T:
        """
        Marks a record as inactive (is_active=False) instead of deleting it.
        Soft delete preserves history and audit trails.

        Args:
            instance: ORM instance to deactivate.

        Returns:
            Updated instance with is_active=False.
        """
        logger.debug(f"[{self.model.__name__}] soft_delete id={instance.id}")
        instance.is_active = False
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    # ── COUNT ────────────────────────────────────────────────────────────────

    async def count_active(self, extra_filters: Optional[list] = None) -> int:
        """
        Counts all active records, optionally with extra filters.

        Args:
            extra_filters: Additional SQLAlchemy WHERE conditions.

        Returns:
            Integer count.
        """
        conditions = [self.model.is_active == True]
        if extra_filters:
            conditions.extend(extra_filters)
        stmt = select(func.count()).select_from(self.model).where(*conditions)
        result = await self.db.execute(stmt)
        return result.scalar_one()
