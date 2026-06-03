"""Unit tests for SQLAlchemy repository implementations."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from powerbi_governance.domain.entities import Dataset, Report, User, Workspace
from powerbi_governance.infrastructure.database.models import Base
from powerbi_governance.infrastructure.repositories import (
    DatasetRepository,
    ReportRepository,
    UserRepository,
    WorkspaceRepository,
)


@pytest.fixture
def db_session() -> Session:
    """Create an isolated in-memory SQLite session for each repository test."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.unit
class TestWorkspaceRepository:
    """Tests for workspace persistence."""

    def test_crud_and_workspace_queries(self, db_session: Session) -> None:
        """CRUD operations should persist and query WorkspaceModel rows."""
        repository = WorkspaceRepository(db_session)
        workspace = repository.create(
            Workspace(
                workspace_id="workspace-1",
                name="Finance",
                description="Finance BI",
                state="ACTIVE",
            )
        )

        assert workspace.id is not None
        assert repository.get_by_id(workspace.id).name == "Finance"
        assert repository.get_by_workspace_id("workspace-1").id == workspace.id
        assert repository.get_all() == [workspace]
        assert repository.get_active_workspaces() == [workspace]

        updated = repository.update(workspace.id, {"name": "Finance Updated", "state": "DELETED"})

        assert updated.name == "Finance Updated"
        assert repository.get_active_workspaces() == []
        assert repository.delete(workspace.id) is True
        assert repository.get_by_id(workspace.id) is None
        assert repository.delete("missing") is False

    def test_create_upserts_by_workspace_id(self, db_session: Session) -> None:
        """Repeated creates with the same workspace_id should update the row."""
        repository = WorkspaceRepository(db_session)
        created = repository.create(Workspace(workspace_id="workspace-1", name="Original"))
        upserted = repository.create(Workspace(workspace_id="workspace-1", name="Upserted", is_premium=True))

        assert upserted.id == created.id
        assert upserted.name == "Upserted"
        assert upserted.is_premium is True
        assert len(repository.get_all()) == 1

    def test_create_rolls_back_on_commit_error(self, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        """Failed writes should rollback the session before re-raising."""
        repository = WorkspaceRepository(db_session)
        rolled_back = False

        def failing_commit() -> None:
            raise RuntimeError("commit failed")

        def mark_rollback() -> None:
            nonlocal rolled_back
            rolled_back = True

        monkeypatch.setattr(db_session, "commit", failing_commit)
        monkeypatch.setattr(db_session, "rollback", mark_rollback)

        with pytest.raises(RuntimeError, match="commit failed"):
            repository.create(Workspace(workspace_id="workspace-1", name="Finance"))

        assert rolled_back is True


@pytest.mark.unit
class TestDatasetRepository:
    """Tests for dataset persistence."""

    def test_get_by_workspace_and_dataset_upsert(self, db_session: Session) -> None:
        """Datasets should be queryable by workspace and upserted by dataset_id."""
        repository = DatasetRepository(db_session)
        created = repository.create(
            Dataset(dataset_id="dataset-1", workspace_id="workspace-1", name="Sales")
        )
        repository.create(Dataset(dataset_id="dataset-2", workspace_id="workspace-2", name="HR"))
        upserted = repository.create(
            Dataset(dataset_id="dataset-1", workspace_id="workspace-1", name="Sales Updated", refresh_count=3)
        )

        assert upserted.id == created.id
        assert upserted.refresh_count == 3
        assert [dataset.dataset_id for dataset in repository.get_by_workspace("workspace-1")] == ["dataset-1"]
        assert len(repository.get_all()) == 2


@pytest.mark.unit
class TestReportRepository:
    """Tests for report persistence."""

    def test_get_by_workspace_and_report_upsert(self, db_session: Session) -> None:
        """Reports should be queryable by workspace and upserted by report_id."""
        repository = ReportRepository(db_session)
        created = repository.create(
            Report(
                report_id="report-1",
                workspace_id="workspace-1",
                dataset_id="dataset-1",
                name="Revenue",
                web_url="https://app.powerbi.com/report-1",
            )
        )
        upserted = repository.create(
            Report(
                report_id="report-1",
                workspace_id="workspace-1",
                dataset_id="dataset-2",
                name="Revenue Updated",
                web_url="https://app.powerbi.com/report-1-updated",
                is_paginated=True,
            )
        )

        assert upserted.id == created.id
        assert upserted.dataset_id == "dataset-2"
        assert upserted.is_paginated is True
        assert repository.get_by_workspace("workspace-1") == [upserted]


@pytest.mark.unit
class TestUserRepository:
    """Tests for user persistence."""

    def test_user_queries_and_upsert(self, db_session: Session) -> None:
        """Users should be queryable by email and upserted by user_id."""
        repository = UserRepository(db_session)
        active_recent = repository.create(
            User(
                user_id="user-1",
                email="active@example.com",
                display_name="Active User",
                last_activity_at=datetime.utcnow(),
            )
        )
        inactive_by_flag = repository.create(
            User(
                user_id="user-2",
                email="inactive@example.com",
                display_name="Inactive User",
                is_active=False,
                last_activity_at=datetime.utcnow(),
            )
        )
        stale_user = repository.create(
            User(
                user_id="user-3",
                email="stale@example.com",
                display_name="Stale User",
                last_activity_at=datetime.utcnow() - timedelta(days=45),
            )
        )
        upserted = repository.create(
            User(
                user_id="user-1",
                email="renamed@example.com",
                display_name="Renamed User",
                last_activity_at=datetime.utcnow(),
            )
        )

        assert upserted.id == active_recent.id
        assert repository.get_by_email("renamed@example.com").display_name == "Renamed User"
        assert repository.get_by_email("active@example.com") is None
        assert {user.id for user in repository.get_inactive_users(days=30)} == {
            inactive_by_flag.id,
            stale_user.id,
        }
