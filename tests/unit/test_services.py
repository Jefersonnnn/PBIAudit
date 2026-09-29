"""
Unit tests for application services.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from powerbi_governance.application.services import (
    ActivityEventsService,
    LicenseService,
    UsageMetricsService,
    UserService,
    WorkspaceService,
)
from powerbi_governance.domain.entities import ActivityEvent, LicenseAssignment, UsageMetric, User, Workspace


class UpsertRepository:
    """Repository fake that records upserted entities."""

    def __init__(self) -> None:
        self.entities = []

    async def upsert(self, entity):
        self.entities.append(entity)
        return entity


class FakeLicenseRepository:
    """Repository fake standing in for LicenseAssignmentRepository's snapshot semantics."""

    def __init__(self) -> None:
        self.assignments: list = []

    def replace_all(self, assignments) -> int:
        self.assignments = list(assignments)
        return len(self.assignments)

    def get_all(self) -> list:
        return self.assignments


class FakeUserRepository:
    """Repository fake standing in for UserRepository, keyed by email."""

    def __init__(self) -> None:
        self.users_by_email: dict = {}

    def create(self, entity):
        self.users_by_email[entity.email] = entity
        return entity

    def get_by_email(self, email: str):
        return self.users_by_email.get(email)


@pytest.mark.unit
class TestWorkspaceService:
    async def test_sync_workspaces_normalizes_and_upserts_powerbi_payload(self):
        powerbi_client = AsyncMock()
        powerbi_client.get_workspaces.return_value = {
            "value": [
                {
                    "id": "workspace-1",
                    "name": "Finance",
                    "description": "Finance reporting",
                    "isOnDedicatedCapacity": True,
                    "capacityId": "capacity-1",
                    "state": "Active",
                },
                {
                    "workspaceId": "workspace-2",
                    "displayName": "Sales",
                    "state": "Deleted",
                },
            ]
        }
        repository = UpsertRepository()

        count = await WorkspaceService(powerbi_client, repository).sync_workspaces()

        assert count == 2
        assert [entity.workspace_id for entity in repository.entities] == ["workspace-1", "workspace-2"]
        assert all(isinstance(entity, Workspace) for entity in repository.entities)
        assert repository.entities[0].is_premium is True
        assert repository.entities[0].capacity_id == "capacity-1"
        assert repository.entities[1].name == "Sales"

    async def test_sync_workspaces_wraps_errors_with_context(self):
        powerbi_client = AsyncMock()
        powerbi_client.get_workspaces.side_effect = RuntimeError("api unavailable")

        with pytest.raises(RuntimeError, match="Workspace synchronization failed"):
            await WorkspaceService(powerbi_client, UpsertRepository()).sync_workspaces()


@pytest.mark.unit
class TestUsageMetricsService:
    async def test_sync_usage_metrics_aggregates_views_and_unique_viewers_per_day(self):
        activity_repository = SimpleNamespace(iter_report_view_events=lambda: iter([
            SimpleNamespace(details={"ReportId": "report-1", "WorkspaceId": "workspace-1"},
                            resource_id="report-1", user_id="A@example.com",
                            event_time=datetime(2026, 6, 1, 10, tzinfo=UTC)),
            SimpleNamespace(details={"ReportId": "report-1", "WorkspaceId": "workspace-1"},
                            resource_id="report-1", user_id="a@example.com",
                            event_time=datetime(2026, 6, 1, 12, tzinfo=UTC)),
            SimpleNamespace(details={"ReportId": "report-1", "WorkspaceId": "workspace-1"},
                            resource_id="report-1", user_id="b@example.com",
                            event_time=datetime(2026, 6, 1, 14, tzinfo=UTC)),
            SimpleNamespace(details={"ReportId": "report-1", "WorkspaceId": "workspace-1"},
                            resource_id="report-1", user_id="b@example.com",
                            event_time=datetime(2026, 6, 2, 9, tzinfo=UTC)),
            SimpleNamespace(details={}, resource_id="report-2", user_id="c@example.com",
                            event_time=datetime(2026, 6, 1, 9, tzinfo=UTC)),
        ]))
        repository = UpsertRepository()

        count = await UsageMetricsService(activity_repository, repository).sync_usage_metrics()

        assert count == 2
        assert len(repository.entities) == 2
        metric = repository.entities[0]
        assert isinstance(metric, UsageMetric)
        assert metric.report_id == "report-1"
        assert metric.workspace_id == "workspace-1"
        assert metric.metric_date == datetime(2026, 6, 1)
        assert metric.views == 3
        assert metric.unique_viewers == 2
        assert repository.entities[1].views == 1

    async def test_sync_usage_metrics_wraps_errors_with_context(self):
        activity_repository = SimpleNamespace(iter_report_view_events=lambda: (_ for _ in ()).throw(RuntimeError("database failed")))

        with pytest.raises(RuntimeError, match="Usage metrics synchronization failed"):
            await UsageMetricsService(activity_repository, UpsertRepository()).sync_usage_metrics()


@pytest.mark.unit
class TestActivityEventsService:
    async def test_sync_activity_events_queries_each_day_window_and_persists_events(self):
        powerbi_client = AsyncMock()
        powerbi_client.get_activity_events.return_value = {
            "activityEventEntities": [
                {
                    "Id": "event-1",
                    "UserId": "USER@EXAMPLE.COM",
                    "Activity": "ViewReport",
                    "ReportId": "report-1",
                    "ArtifactName": "Executive",
                    "CreationTime": "2026-06-02T10:00:00Z",
                }
            ]
        }
        repository = UpsertRepository()

        count = await ActivityEventsService(powerbi_client, repository).sync_activity_events(days_back=2)

        assert count == 2
        assert powerbi_client.get_activity_events.await_count == 2
        for call in powerbi_client.get_activity_events.await_args_list:
            start = call.kwargs["start_date_time"]
            end = call.kwargs["end_date_time"]
            assert start[:10] == end[:10]  # same UTC calendar day, per the API's requirement
            assert start.endswith("Z") and end.endswith("Z")
        assert len(repository.entities) == 2
        event = repository.entities[0]
        assert isinstance(event, ActivityEvent)
        assert event.event_id == "event-1"
        assert event.user_id == "user@example.com"
        assert event.activity == "ViewReport"
        assert event.resource_id == "report-1"

    async def test_sync_activity_events_follows_continuation_token_for_same_day(self):
        powerbi_client = AsyncMock()
        powerbi_client.get_activity_events.side_effect = [
            {
                "activityEventEntities": [{"Id": "event-1", "UserId": "a@example.com", "CreationTime": "2026-06-02T01:00:00Z"}],
                "continuationUri": "https://api.powerbi.com/v1.0/myorg/admin/activityevents?continuationToken=abc",
            },
            {
                "activityEventEntities": [{"Id": "event-2", "UserId": "b@example.com", "CreationTime": "2026-06-02T02:00:00Z"}],
            },
        ]
        repository = UpsertRepository()

        count = await ActivityEventsService(powerbi_client, repository).sync_activity_events(days_back=1)

        assert count == 2
        assert powerbi_client.get_activity_events.await_count == 2
        first_call, second_call = powerbi_client.get_activity_events.await_args_list
        assert "start_date_time" in first_call.kwargs
        assert second_call.kwargs.get("continuation_uri") == (
            "https://api.powerbi.com/v1.0/myorg/admin/activityevents?continuationToken=abc"
        )

    async def test_sync_activity_events_rejects_invalid_days_back(self):
        with pytest.raises(RuntimeError, match="days_back must be at least 1"):
            await ActivityEventsService(AsyncMock(), UpsertRepository()).sync_activity_events(days_back=0)

    async def test_sync_activity_events_rejects_days_back_beyond_28_day_retention(self):
        with pytest.raises(RuntimeError, match="days_back cannot exceed 28"):
            await ActivityEventsService(AsyncMock(), UpsertRepository()).sync_activity_events(days_back=29)


@pytest.mark.unit
class TestUserService:
    async def test_identify_inactive_users_combines_graph_powerbi_and_persisted_activity(self):
        graph_client = AsyncMock()
        graph_client.get_users.return_value = {
            "value": [
                {
                    "id": "graph-active",
                    "mail": "active@example.com",
                    "displayName": "Active User",
                    "accountEnabled": True,
                },
                {
                    "id": "graph-inactive",
                    "mail": "inactive@example.com",
                    "displayName": "Inactive User",
                    "accountEnabled": True,
                },
            ]
        }
        powerbi_client = AsyncMock()
        powerbi_client.get_workspaces.return_value = {"value": [{"id": "workspace-1"}]}
        powerbi_client.get_workspace_users.return_value = {
            "value": [
                {
                    "identifier": "powerbi-only@example.com",
                    "displayName": "Power BI Only",
                    "groupUserAccessRight": "Viewer",
                }
            ]
        }

        class ActivityRepository:
            async def get_activity_events(self):
                return [
                    {
                        "user_id": "graph-active",
                        "event_time": datetime.now(UTC) - timedelta(days=2),
                    },
                    {
                        "user_id": "powerbi-only@example.com",
                        "event_time": datetime.now(UTC) - timedelta(days=90),
                    },
                ]

        inactive_users = await UserService(
            graph_client,
            powerbi_client,
            ActivityRepository(),
        ).identify_inactive_users(days_inactive=30)

        assert all(isinstance(user, User) for user in inactive_users)
        assert {user.email for user in inactive_users} == {"inactive@example.com", "powerbi-only@example.com"}
        powerbi_client.get_workspace_users.assert_awaited_once_with("workspace-1")

    async def test_identify_inactive_users_wraps_errors_with_context(self):
        graph_client = AsyncMock()
        graph_client.get_users.side_effect = RuntimeError("graph failed")

        with pytest.raises(RuntimeError, match="Inactive users identification failed"):
            await UserService(graph_client, AsyncMock(), UpsertRepository()).identify_inactive_users()


@pytest.mark.unit
class TestLicenseService:
    async def test_sync_license_assignments_filters_to_pro_plans_and_dedupes(self):
        graph_client = AsyncMock()
        graph_client.get_subscribed_skus.return_value = {
            "value": [
                {
                    "servicePlans": [
                        {"servicePlanId": "plan-pro", "servicePlanName": "BI_AZURE_P2"},
                        {"servicePlanId": "plan-free", "servicePlanName": "BI_AZURE_P0"},
                        {"servicePlanId": "plan-ppu", "servicePlanName": "PBI_PREMIUM_PER_USER"},
                        {"servicePlanId": "plan-exchange", "servicePlanName": "EXCHANGE_S_STANDARD"},
                    ]
                }
            ]
        }
        graph_client.get_all_users_with_licenses.return_value = [
            {
                "id": "user-1",
                "mail": "pro@example.com",
                "displayName": "Pro User",
                "accountEnabled": True,
                "jobTitle": "Analista Financeiro",
                "department": "Financeiro",
                "assignedPlans": [
                    {"capabilityStatus": "Enabled", "servicePlanId": "plan-pro"},
                    {"capabilityStatus": "Enabled", "servicePlanId": "plan-pro"},
                    {"capabilityStatus": "Enabled", "servicePlanId": "plan-exchange"},
                    {"capabilityStatus": "Deleted", "servicePlanId": "plan-pro"},
                ],
            },
            {
                "id": "user-2",
                "mail": "nolicense@example.com",
                "displayName": "No License",
                "accountEnabled": True,
                "assignedPlans": [{"capabilityStatus": "Enabled", "servicePlanId": "plan-exchange"}],
            },
            {
                "id": "user-3",
                "mail": "free@example.com",
                "displayName": "Free User",
                "accountEnabled": True,
                "assignedPlans": [{"capabilityStatus": "Enabled", "servicePlanId": "plan-free"}],
            },
            {
                "id": "user-4",
                "mail": "ppu@example.com",
                "displayName": "PPU User",
                "accountEnabled": True,
                "assignedPlans": [{"capabilityStatus": "Enabled", "servicePlanId": "plan-ppu"}],
            },
        ]

        repository = FakeLicenseRepository()
        user_repository = FakeUserRepository()
        count = await LicenseService(graph_client, repository, user_repository).sync_license_assignments()

        # only Power BI Pro counts against the tenant's fixed seat pool - Free doesn't
        # consume a seat, and Premium/Premium Per User are tracked separately
        assert count == 1
        assert len(repository.assignments) == 1
        assignment = repository.assignments[0]
        assert isinstance(assignment, LicenseAssignment)
        assert assignment.email == "pro@example.com"
        assert assignment.license_type == "Power BI Pro"
        assert assignment.service_plan_name == "BI_AZURE_P2"

        # every user's profile is persisted, not just the ones with a tracked license
        assert user_repository.get_by_email("pro@example.com").job_title == "Analista Financeiro"
        assert user_repository.get_by_email("pro@example.com").department == "Financeiro"
        assert user_repository.get_by_email("nolicense@example.com") is not None
        assert user_repository.get_by_email("free@example.com") is not None
        assert user_repository.get_by_email("ppu@example.com") is not None

    async def test_sync_license_assignments_wraps_errors_with_context(self):
        graph_client = AsyncMock()
        graph_client.get_subscribed_skus.side_effect = RuntimeError("graph failed")

        with pytest.raises(RuntimeError, match="License assignment synchronization failed"):
            await LicenseService(graph_client, FakeLicenseRepository()).sync_license_assignments()

    def test_build_usage_report_flags_idle_and_never_used_licenses_first(self):
        repository = FakeLicenseRepository()
        repository.assignments = [
            LicenseAssignment(
                user_id="user-1",
                email="active@example.com",
                display_name="Active",
                license_type="Power BI Pro",
                service_plan_name="BI_AZURE_P2",
            ),
            LicenseAssignment(
                user_id="user-2",
                email="idle@example.com",
                display_name="Idle",
                license_type="Power BI Pro",
                service_plan_name="BI_AZURE_P2",
            ),
        ]
        activity_summary = {
            "active@example.com": {
                "last_access": datetime.utcnow() - timedelta(days=1),
                "resources": {"Executive Dashboard"},
            }
        }
        user_repository = FakeUserRepository()
        user_repository.create(
            User(
                user_id="user-1",
                email="active@example.com",
                display_name="Active",
                job_title="Gerente de Vendas",
                department="Comercial",
            )
        )

        rows = LicenseService(AsyncMock(), repository, user_repository).build_usage_report(activity_summary)

        assert [row.email for row in rows] == ["idle@example.com", "active@example.com"]
        never_used_row = rows[0]
        assert never_used_row.last_access is None
        assert never_used_row.days_since_access is None
        assert never_used_row.resources == []
        assert never_used_row.job_title is None  # no profile synced for this user

        active_row = rows[1]
        assert active_row.days_since_access == 1
        assert active_row.resources == ["Executive Dashboard"]
        assert active_row.job_title == "Gerente de Vendas"
        assert active_row.department == "Comercial"

    def test_summarize_by_department_aggregates_and_ranks_by_idle_percentage(self):
        repository = FakeLicenseRepository()
        repository.assignments = [
            LicenseAssignment(
                user_id="user-1",
                email="active@example.com",
                display_name="Active",
                license_type="Power BI Pro",
                service_plan_name="BI_AZURE_P2",
            ),
            LicenseAssignment(
                user_id="user-2",
                email="idle@example.com",
                display_name="Idle",
                license_type="Power BI Pro",
                service_plan_name="BI_AZURE_P2",
            ),
            LicenseAssignment(
                user_id="user-3",
                email="never-used@example.com",
                display_name="Never Used",
                license_type="Power BI Pro",
                service_plan_name="BI_AZURE_P2",
            ),
            LicenseAssignment(
                user_id="user-4",
                email="no-department@example.com",
                display_name="No Department",
                license_type="Power BI Pro",
                service_plan_name="BI_AZURE_P2",
            ),
        ]
        activity_summary = {
            "active@example.com": {
                "last_access": datetime.utcnow() - timedelta(days=1),
                "resources": {"Executive Dashboard"},
            },
            "idle@example.com": {
                "last_access": datetime.utcnow() - timedelta(days=60),
                "resources": {"Sales Dashboard"},
            },
        }
        user_repository = FakeUserRepository()
        user_repository.create(
            User(user_id="user-1", email="active@example.com", display_name="Active", department="Comercial")
        )
        user_repository.create(
            User(user_id="user-2", email="idle@example.com", display_name="Idle", department="Comercial")
        )
        user_repository.create(
            User(
                user_id="user-3",
                email="never-used@example.com",
                display_name="Never Used",
                department="Financeiro",
            )
        )
        # user-4 has no persisted profile, so it falls into the "no department" bucket

        service = LicenseService(AsyncMock(), repository, user_repository)
        rows = service.build_usage_report(activity_summary)
        summaries = service.summarize_by_department(rows, inactive_days=30)

        by_department = {summary.department: summary for summary in summaries}

        assert by_department["Financeiro"].total_licenses == 1
        assert by_department["Financeiro"].never_used_count == 1
        assert by_department["Financeiro"].idle_percentage == 100.0

        assert by_department["Sem departamento"].total_licenses == 1
        assert by_department["Sem departamento"].idle_percentage == 100.0

        comercial = by_department["Comercial"]
        assert comercial.total_licenses == 2
        assert comercial.active_count == 1
        assert comercial.idle_count == 1
        assert comercial.never_used_count == 0
        assert comercial.idle_percentage == 50.0

        # ranked with the highest idle percentage first; ties broken by more licenses
        assert [summary.department for summary in summaries][:2] == ["Financeiro", "Sem departamento"] or [
            summary.department for summary in summaries
        ][:2] == ["Sem departamento", "Financeiro"]
        assert summaries[-1].department == "Comercial"
