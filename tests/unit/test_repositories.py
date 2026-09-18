"""Unit tests for SQLAlchemy repository implementations."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from powerbi_governance.domain.entities import ActivityEvent, LicenseAssignment, UsageMetric, User, Workspace
from powerbi_governance.infrastructure.database.models import Base
from powerbi_governance.infrastructure.repositories import (
    ActivityEventRepository,
    LicenseAssignmentRepository,
    UsageMetricRepository,
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
class TestUsageMetricRepository:
    """Tests for usage metric persistence."""

    def test_get_by_workspace_and_upsert_by_report_and_date(self, db_session: Session) -> None:
        """Usage metrics should be queryable by workspace and upserted by (report_id, metric_date)."""
        repository = UsageMetricRepository(db_session)
        metric_date = datetime(2026, 6, 1)
        created = repository.create(
            UsageMetric(
                report_id="report-1",
                workspace_id="workspace-1",
                metric_date=metric_date,
                views=10,
                unique_viewers=2,
            )
        )
        repository.create(
            UsageMetric(
                report_id="report-2",
                workspace_id="workspace-2",
                metric_date=metric_date,
                views=1,
                unique_viewers=1,
            )
        )
        upserted = repository.create(
            UsageMetric(
                report_id="report-1",
                workspace_id="workspace-1",
                metric_date=metric_date,
                views=42,
                unique_viewers=7,
            )
        )

        assert upserted.id == created.id
        assert upserted.views == 42
        assert [metric.report_id for metric in repository.get_by_workspace("workspace-1")] == ["report-1"]
        assert len(repository.get_all()) == 2


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
                job_title="Analista de Dados",
                department="TI",
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
        # job_title/department from the original create survive an update that omits them
        assert repository.get_by_email("renamed@example.com").job_title == "Analista de Dados"
        assert repository.get_by_email("renamed@example.com").department == "TI"


@pytest.mark.unit
class TestLicenseAssignmentRepository:
    """Tests for license assignment snapshot persistence."""

    def test_replace_all_swaps_the_full_snapshot(self, db_session: Session) -> None:
        """Each sync should fully replace prior assignments, not accumulate them."""
        repository = LicenseAssignmentRepository(db_session)
        repository.replace_all(
            [
                LicenseAssignment(
                    user_id="user-1",
                    email="pro@example.com",
                    display_name="Pro User",
                    license_type="Power BI Pro",
                    service_plan_name="BI_AZURE_P2",
                )
            ]
        )
        assert [a.email for a in repository.get_all()] == ["pro@example.com"]

        count = repository.replace_all(
            [
                LicenseAssignment(
                    user_id="user-2",
                    email="ppu@example.com",
                    display_name="PPU User",
                    license_type="Power BI Premium Per User",
                    service_plan_name="PBI_PREMIUM_PER_USER",
                )
            ]
        )

        assert count == 1
        assert [a.email for a in repository.get_all()] == ["ppu@example.com"]


@pytest.mark.unit
class TestActivityEventRepository:
    """Tests for activity event persistence and per-user aggregation."""

    def test_get_usage_summary_by_user_aggregates_last_access_and_resources(self, db_session: Session) -> None:
        """Summary should group by lowercased user_id and collect distinct resources."""
        repository = ActivityEventRepository(db_session)
        repository.create(
            ActivityEvent(
                event_id="event-1",
                user_id="user@example.com",
                activity="ViewReport",
                resource_name="Executive Dashboard",
                event_time=datetime.utcnow() - timedelta(days=10),
            )
        )
        repository.create(
            ActivityEvent(
                event_id="event-2",
                user_id="USER@EXAMPLE.COM",
                activity="ViewReport",
                resource_name="Sales Dashboard",
                event_time=datetime.utcnow() - timedelta(days=1),
            )
        )

        summary = repository.get_usage_summary_by_user()

        assert set(summary.keys()) == {"user@example.com"}
        entry = summary["user@example.com"]
        assert entry["resources"] == {"Executive Dashboard", "Sales Dashboard"}
        assert entry["last_access"] > datetime.utcnow() - timedelta(days=2)
