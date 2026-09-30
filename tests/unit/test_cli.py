"""CLI command tests."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

import powerbi_governance.interfaces.cli as cli_module
from powerbi_governance.interfaces.cli import app

runner = CliRunner()


class _Context(SimpleNamespace):
    def close(self):
        self.closed = True


def _make_context():
    async def get_workspaces(skip=0, top=100):
        return {
            "value": [
                {"id": "ws-1", "name": "Finance", "isOnDedicatedCapacity": True},
                {"id": "ws-2", "name": "Operations", "isOnDedicatedCapacity": False},
            ]
        }

    return _Context(
        powerbi_client=SimpleNamespace(get_workspaces=get_workspaces),
        xmla_client=object(),
        workspace_repository=object(),
        usage_metric_repository=object(),
        activity_event_repository=SimpleNamespace(get_usage_summary_by_user=lambda: {}),
        license_repository=object(),
        user_repository=object(),
        closed=False,
    )


def test_sync_workspaces_runs_service_and_prints_count(monkeypatch):
    """sync-workspaces invokes the real use-case service from the CLI layer."""
    context = _make_context()
    service = Mock()

    async def sync_workspaces():
        return 7

    service.sync_workspaces = Mock(side_effect=sync_workspaces)
    service_factory = Mock(return_value=service)

    monkeypatch.setattr(cli_module, "_build_cli_context", Mock(return_value=context))
    monkeypatch.setattr(cli_module, "WorkspaceService", service_factory)

    result = runner.invoke(app, ["sync-workspaces"])

    assert result.exit_code == 0
    assert "Synchronized 7 workspaces" in result.output
    service_factory.assert_called_once_with(context.powerbi_client, context.workspace_repository)
    service.sync_workspaces.assert_called_once_with()
    assert context.closed is True


def test_sync_usage_metrics_wires_activity_and_metric_repositories(monkeypatch):
    """sync-usage-metrics wires the usage metrics service dependencies."""
    context = _make_context()
    service = Mock()

    async def sync_usage_metrics():
        return 3

    service.sync_usage_metrics = Mock(side_effect=sync_usage_metrics)
    service_factory = Mock(return_value=service)

    local_context_builder = Mock(return_value=context)
    remote_context_builder = Mock(side_effect=AssertionError("remote context must not be created"))
    monkeypatch.setattr(cli_module, "_build_local_report_context", local_context_builder)
    monkeypatch.setattr(cli_module, "_build_cli_context", remote_context_builder)
    monkeypatch.setattr(cli_module, "UsageMetricsService", service_factory)

    result = runner.invoke(app, ["sync-usage-metrics"])

    assert result.exit_code == 0
    assert "Synchronized 3 usage metrics" in result.output
    service_factory.assert_called_once_with(
        context.activity_event_repository,
        context.usage_metric_repository,
    )
    service.sync_usage_metrics.assert_called_once_with()
    local_context_builder.assert_called_once_with()
    remote_context_builder.assert_not_called()
    assert context.closed is True


def test_sync_activity_events_passes_days_back(monkeypatch):
    """sync-activity-events forwards the days-back option to the service."""
    context = _make_context()
    service = Mock()

    async def sync_activity_events(days_back=1):
        return days_back + 10

    service.sync_activity_events = Mock(side_effect=sync_activity_events)
    service_factory = Mock(return_value=service)

    monkeypatch.setattr(cli_module, "_build_cli_context", Mock(return_value=context))
    monkeypatch.setattr(cli_module, "ActivityEventsService", service_factory)

    result = runner.invoke(app, ["sync-activity-events", "5"])

    assert result.exit_code == 0
    assert "Synchronized 15 activity events" in result.output
    service_factory.assert_called_once_with(context.powerbi_client, context.activity_event_repository)
    service.sync_activity_events.assert_called_once_with(days_back=5)
    assert context.closed is True


def test_list_workspaces_fetches_data_and_populates_table(monkeypatch):
    """list-workspaces fetches real data from the Power BI client and renders it."""
    context = _make_context()
    build_context = Mock(return_value=context)
    monkeypatch.setattr(cli_module, "_build_cli_context", build_context)

    result = runner.invoke(app, ["list-workspaces", "1", "2"])

    assert result.exit_code == 0
    assert "Finance" in result.output
    assert "Operations" in result.output
    assert "Listed 2 workspaces (skip=1, top=2)" in result.output
    build_context.assert_called_once_with()
    assert context.closed is True


def test_build_local_report_context_skips_remote_authentication(monkeypatch):
    """Local report dependencies are assembled without creating remote clients or tokens."""
    settings = SimpleNamespace()
    session = Mock()
    database_manager = Mock()
    database_manager.get_session.return_value = session

    monkeypatch.setattr(cli_module, "get_settings", Mock(return_value=settings))
    configure_logging = Mock()
    monkeypatch.setattr(cli_module, "configure_logging", configure_logging)
    monkeypatch.setattr(cli_module, "DatabaseManager", Mock(return_value=database_manager))
    powerbi_authenticator = Mock()
    graph_authenticator = Mock()
    monkeypatch.setattr(cli_module, "MsalAuthenticator", powerbi_authenticator)
    monkeypatch.setattr(cli_module, "MsalGraphAuthenticator", graph_authenticator)
    powerbi_client = Mock()
    graph_client = Mock()
    xmla_client = Mock()
    monkeypatch.setattr(cli_module, "PowerBIClient", powerbi_client)
    monkeypatch.setattr(cli_module, "GraphClient", graph_client)
    monkeypatch.setattr(cli_module, "XmlaClient", xmla_client)

    context = cli_module._build_local_report_context()

    configure_logging.assert_called_once_with(settings)
    database_manager.initialize.assert_called_once_with()
    database_manager.get_session.assert_called_once_with()
    assert context.session is session
    powerbi_authenticator.assert_not_called()
    graph_authenticator.assert_not_called()
    powerbi_client.assert_not_called()
    graph_client.assert_not_called()
    xmla_client.assert_not_called()


@pytest.mark.parametrize(
    "command", ["license-report", "department-report", "export-report"]
)
def test_local_report_commands_do_not_build_remote_context(monkeypatch, command):
    """All report commands use only the local database context."""
    context = _make_context()
    local_context_builder = Mock(return_value=context)
    remote_context_builder = Mock(side_effect=AssertionError("remote context must not be created"))
    license_service = Mock()
    license_service.build_usage_report.return_value = []

    monkeypatch.setattr(cli_module, "_build_local_report_context", local_context_builder)
    monkeypatch.setattr(cli_module, "_build_cli_context", remote_context_builder)
    monkeypatch.setattr(cli_module, "LicenseService", Mock(return_value=license_service))

    result = runner.invoke(app, [command])

    assert result.exit_code == 0
    local_context_builder.assert_called_once_with()
    remote_context_builder.assert_not_called()
    assert context.closed is True


def test_build_cli_context_creates_auth_clients_database_and_repositories(monkeypatch):
    """The helper assembles settings, logging, authenticators, clients, DB and repositories."""
    settings = SimpleNamespace()
    session = Mock()
    database_manager = Mock()
    database_manager.get_session.return_value = session

    powerbi_authenticator = Mock()
    powerbi_authenticator.authenticate.return_value = {"access_token": "powerbi-token"}
    graph_authenticator = Mock()
    graph_authenticator.authenticate.return_value = {"access_token": "graph-token"}

    powerbi_client = Mock()
    graph_client = Mock()
    xmla_client = Mock()
    workspace_repository = Mock()
    usage_metric_repository = Mock()
    activity_event_repository = Mock()

    monkeypatch.setattr(cli_module, "get_settings", Mock(return_value=settings))
    configure_logging = Mock()
    monkeypatch.setattr(cli_module, "configure_logging", configure_logging)
    monkeypatch.setattr(cli_module, "MsalAuthenticator", Mock(return_value=powerbi_authenticator))
    monkeypatch.setattr(cli_module, "MsalGraphAuthenticator", Mock(return_value=graph_authenticator))
    monkeypatch.setattr(cli_module, "PowerBIClient", Mock(return_value=powerbi_client))
    monkeypatch.setattr(cli_module, "GraphClient", Mock(return_value=graph_client))
    monkeypatch.setattr(cli_module, "XmlaClient", Mock(return_value=xmla_client))
    monkeypatch.setattr(cli_module, "DatabaseManager", Mock(return_value=database_manager))
    monkeypatch.setattr(cli_module, "WorkspaceRepository", Mock(return_value=workspace_repository))
    monkeypatch.setattr(cli_module, "UsageMetricRepository", Mock(return_value=usage_metric_repository))
    monkeypatch.setattr(cli_module, "ActivityEventRepository", Mock(return_value=activity_event_repository))

    context = cli_module._build_cli_context()

    configure_logging.assert_called_once_with(settings)
    cli_module.MsalAuthenticator.assert_called_once_with(settings)
    cli_module.MsalGraphAuthenticator.assert_called_once_with(settings)
    cli_module.PowerBIClient.assert_called_once_with(settings, "powerbi-token")
    cli_module.GraphClient.assert_called_once_with(settings, "graph-token")
    cli_module.XmlaClient.assert_called_once_with(settings)
    database_manager.initialize.assert_called_once_with()
    database_manager.get_session.assert_called_once_with()
    cli_module.WorkspaceRepository.assert_called_once_with(session)
    cli_module.UsageMetricRepository.assert_called_once_with(session)
    cli_module.ActivityEventRepository.assert_called_once_with(session)
    assert context.powerbi_client is powerbi_client
    assert context.graph_client is graph_client
    assert context.xmla_client is xmla_client
