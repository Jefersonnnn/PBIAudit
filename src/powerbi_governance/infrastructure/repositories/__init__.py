"""
Repository pattern implementations for data access.

The repositories in this module are concrete SQLAlchemy implementations.  Each
write operation owns its transaction boundary: successful mutations are
committed and refreshed, while failed mutations rollback the current session
before re-raising the original exception.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar, Optional, List
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from powerbi_governance.infrastructure.database.models import (
    DatasetModel,
    ReportModel,
    UserModel,
    WorkspaceModel,
)

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """
    Concrete base repository with common CRUD operations.

    Subclasses bind ``model_class`` to a SQLAlchemy ORM model and optionally
    ``external_key`` to the unique Power BI identifier used for upserts.
    """

    model_class: type[ModelT]
    external_key: str | None = None

    def __init__(self, session: Session) -> None:
        """
        Initialize repository.

        Args:
            session: SQLAlchemy session used by this repository.
        """
        self.session = session

    def get_by_id(self, id: str) -> ModelT | None:
        """Get entity by internal database ID."""
        return self.session.get(self.model_class, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelT]:
        """Get all entities with pagination."""
        statement = select(self.model_class).offset(skip).limit(limit)
        return list(self.session.scalars(statement).all())

    def create(self, entity: ModelT | dict[str, Any]) -> ModelT:
        """
        Create an entity, or update the existing row with the same Power BI key.

        This gives Power BI identifiers such as ``workspace_id`` and
        ``dataset_id`` explicit upsert behavior: calling ``create`` repeatedly
        with the same external key updates the existing row instead of creating
        duplicates or surfacing a unique-constraint error.
        """
        data = self._entity_to_dict(entity)
        existing = self._get_existing_by_external_key(data)

        try:
            if existing is not None:
                self._apply_data(existing, data, preserve_internal_id=True)
                self.session.add(existing)
                self.session.commit()
                self.session.refresh(existing)
                return existing

            data.setdefault("id", str(uuid4()))
            instance = self.model_class(**data)
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except Exception:
            self.session.rollback()
            raise

    def update(self, id: str, entity: ModelT | dict[str, Any]) -> ModelT | None:
        """Update an entity by internal database ID."""
        instance = self.get_by_id(id)
        if instance is None:
            return None

        try:
            self._apply_data(instance, self._entity_to_dict(entity), preserve_internal_id=True)
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except Exception:
            self.session.rollback()
            raise

    def delete(self, id: str) -> bool:
        """Delete an entity by internal database ID."""
        instance = self.get_by_id(id)
        if instance is None:
            return False

        try:
            self.session.delete(instance)
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            raise

    def _get_existing_by_external_key(self, data: dict[str, Any]) -> ModelT | None:
        """Return an existing row that matches this repository's Power BI key."""
        if self.external_key is None or self.external_key not in data:
            return None

        statement = select(self.model_class).where(
            getattr(self.model_class, self.external_key) == data[self.external_key]
        )
        return self.session.scalars(statement).first()

    def _entity_to_dict(self, entity: ModelT | dict[str, Any]) -> dict[str, Any]:
        """Convert supported entity inputs into model constructor/update data."""
        if isinstance(entity, dict):
            raw_data = dict(entity)
        elif hasattr(entity, "model_dump"):
            raw_data = entity.model_dump()
        else:
            raw_data = {
                column.name: getattr(entity, column.name)
                for column in self.model_class.__table__.columns
                if hasattr(entity, column.name)
            }

        model_columns = {column.name for column in self.model_class.__table__.columns}
        return {
            key: str(value) if key == "id" and value is not None else value
            for key, value in raw_data.items()
            if key in model_columns and value is not None
        }

    @staticmethod
    def _apply_data(instance: ModelT, data: dict[str, Any], *, preserve_internal_id: bool) -> None:
        """Apply entity data to an ORM model instance."""
        for key, value in data.items():
            if preserve_internal_id and key == "id":
                continue
            setattr(instance, key, value)


class WorkspaceRepository(BaseRepository[WorkspaceModel]):
    """Repository for workspace operations."""

    model_class = WorkspaceModel
    external_key = "workspace_id"

    def get_by_workspace_id(self, workspace_id: str) -> WorkspaceModel | None:
        """Get workspace by Power BI workspace ID."""
        statement = select(WorkspaceModel).where(WorkspaceModel.workspace_id == workspace_id)
        return self.session.scalars(statement).first()

    def get_active_workspaces(self) -> list[WorkspaceModel]:
        """Get all active workspaces."""
        statement = select(WorkspaceModel).where(WorkspaceModel.state == "ACTIVE")
        return list(self.session.scalars(statement).all())


class DatasetRepository(BaseRepository[DatasetModel]):
    """Repository for dataset operations."""

    model_class = DatasetModel
    external_key = "dataset_id"

    def get_by_workspace(self, workspace_id: str) -> list[DatasetModel]:
        """Get datasets in a workspace by Power BI workspace ID."""
        statement = select(DatasetModel).where(DatasetModel.workspace_id == workspace_id)
        return list(self.session.scalars(statement).all())


class ReportRepository(BaseRepository[ReportModel]):
    """Repository for report operations."""

    model_class = ReportModel
    external_key = "report_id"

    def get_by_workspace(self, workspace_id: str) -> list[ReportModel]:
        """Get reports in a workspace by Power BI workspace ID."""
        statement = select(ReportModel).where(ReportModel.workspace_id == workspace_id)
        return list(self.session.scalars(statement).all())


class UserRepository(BaseRepository[UserModel]):
    """Repository for user operations."""

    model_class = UserModel
    external_key = "user_id"

    def get_by_email(self, email: str) -> UserModel | None:
        """Get user by email."""
        statement = select(UserModel).where(UserModel.email == email)
        return self.session.scalars(statement).first()

    def get_inactive_users(self, days: int = 30) -> list[UserModel]:
        """Get users marked inactive or without activity in the given window."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        statement = select(UserModel).where(
            or_(
                UserModel.is_active.is_(False),
                UserModel.last_activity_at.is_(None),
                UserModel.last_activity_at <= cutoff,
            )
        )
        return list(self.session.scalars(statement).all())


class UsageMetricRepository(BaseRepository[ModelT]):
    """Repository for usage metric operations"""

    def get_by_id(self, id: str) -> Optional[ModelT]:
        """Get usage metric by ID"""
        pass

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelT]:
        """Get all usage metrics"""
        pass

    def create(self, entity: ModelT) -> ModelT:
        """Create new usage metric"""
        pass

    def update(self, id: str, entity: ModelT) -> Optional[ModelT]:
        """Update usage metric"""
        pass

    def delete(self, id: str) -> bool:
        """Delete usage metric"""
        pass

    def get_by_workspace(self, workspace_id: str) -> List[ModelT]:
        """Get usage metrics for a workspace"""
        pass


class ActivityEventRepository(BaseRepository[ModelT]):
    """Repository for activity event operations"""

    def get_by_id(self, id: str) -> Optional[ModelT]:
        """Get activity event by ID"""
        pass

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelT]:
        """Get all activity events"""
        pass

    def create(self, entity: ModelT) -> ModelT:
        """Create new activity event"""
        pass

    def update(self, id: str, entity: ModelT) -> Optional[ModelT]:
        """Update activity event"""
        pass

    def delete(self, id: str) -> bool:
        """Delete activity event"""
        pass

    def get_recent_events(self, days: int = 1) -> List[ModelT]:
        """Get recent activity events"""
        pass


__all__ = [
    "BaseRepository",
    "WorkspaceRepository",
    "DatasetRepository",
    "ReportRepository",
    "UserRepository",
    "UsageMetricRepository",
    "ActivityEventRepository",
]
