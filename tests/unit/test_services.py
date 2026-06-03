"""
Unit tests for application services.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from powerbi_governance.application.services import (
    ActivityEventsService,
    UsageMetricsService,
    UserService,
    WorkspaceService,
)
from powerbi_governance.domain.entities import ActivityEvent, UsageMetric, User, Workspace


class UpsertRepository:
    """Repository fake that records upserted entities."""

    def __init__(self) -> None:
        self.entities = []

    async def upsert(self, entity):
        self.entities.append(entity)
        return entity


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
    async def test_sync_usage_metrics_walks_workspaces_datasets_reports_and_persists_metrics(self):
        powerbi_client = AsyncMock()
        powerbi_client.get_workspaces.return_value = {"value": [{"id": "workspace-1", "name": "Finance"}]}
        powerbi_client.get_workspace_datasets.return_value = {
            "value": [{"id": "dataset-1", "name": "Semantic model"}]
        }
        powerbi_client.get_workspace_reports.return_value = {
            "value": [{"id": "report-1", "datasetId": "dataset-1", "name": "Executive"}]
        }
        xmla_client = AsyncMock()
        xmla_client.get_usage_metrics_table.return_value = {
            "rows": [
                {
                    "ReportId": "report-1",
                    "Date": "2026-06-01T00:00:00Z",
                    "Views": 42,
                    "UniqueViewers": 7,
                }
            ]
        }
        repository = UpsertRepository()

        count = await UsageMetricsService(powerbi_client, xmla_client, repository).sync_usage_metrics()

        assert count == 1
        powerbi_client.get_workspace_datasets.assert_awaited_once_with("workspace-1")
        powerbi_client.get_workspace_reports.assert_awaited_once_with("workspace-1")
        xmla_client.get_usage_metrics_table.assert_awaited_once_with("dataset-1")
        assert len(repository.entities) == 1
        metric = repository.entities[0]
        assert isinstance(metric, UsageMetric)
        assert metric.report_id == "report-1"
        assert metric.workspace_id == "workspace-1"
        assert metric.views == 42
        assert metric.unique_viewers == 7

    async def test_sync_usage_metrics_wraps_errors_with_context(self):
        powerbi_client = AsyncMock()
        powerbi_client.get_workspaces.return_value = {"value": [{"id": "workspace-1"}]}
        powerbi_client.get_workspace_datasets.side_effect = RuntimeError("datasets failed")
        xmla_client = AsyncMock()

        with pytest.raises(RuntimeError, match="Usage metrics synchronization failed"):
            await UsageMetricsService(powerbi_client, xmla_client, UpsertRepository()).sync_usage_metrics()


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
        assert all("ActivityDateTime ge datetime" in call.args[0] for call in powerbi_client.get_activity_events.await_args_list)
        assert len(repository.entities) == 2
        event = repository.entities[0]
        assert isinstance(event, ActivityEvent)
        assert event.event_id == "event-1"
        assert event.user_id == "user@example.com"
        assert event.activity == "ViewReport"
        assert event.resource_id == "report-1"

    async def test_sync_activity_events_rejects_invalid_days_back(self):
        with pytest.raises(RuntimeError, match="days_back must be at least 1"):
            await ActivityEventsService(AsyncMock(), UpsertRepository()).sync_activity_events(days_back=0)


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
