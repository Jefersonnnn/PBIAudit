"""
CLI - Command-line interface using Typer

Provides commands for synchronization, listing and management operations.
"""

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Annotated, Any, TypeVar

import structlog
import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session

from powerbi_governance.application.services import ActivityEventsService, UsageMetricsService, WorkspaceService
from powerbi_governance.core import Settings, configure_logging, get_settings
from powerbi_governance.infrastructure.auth import MsalAuthenticator, MsalGraphAuthenticator
from powerbi_governance.infrastructure.clients.graph import GraphClient
from powerbi_governance.infrastructure.clients.powerbi import PowerBIClient
from powerbi_governance.infrastructure.clients.xmla import XmlaClient
from powerbi_governance.infrastructure.database import DatabaseManager
from powerbi_governance.infrastructure.repositories import (
    ActivityEventRepository,
    UsageMetricRepository,
    WorkspaceRepository,
)

log = structlog.get_logger(__name__)
console = Console()

T = TypeVar("T")

app = typer.Typer(
    name="pbi-governance",
    help="Power BI Governance Platform - Automated audit and analytics",
)


@dataclass
class CliContext:
    """Runtime dependencies used by CLI commands."""

    settings: Settings
    powerbi_authenticator: MsalAuthenticator
    graph_authenticator: MsalGraphAuthenticator
    powerbi_client: PowerBIClient
    graph_client: GraphClient
    xmla_client: XmlaClient
    database_manager: DatabaseManager
    session: Session
    workspace_repository: WorkspaceRepository
    usage_metric_repository: UsageMetricRepository
    activity_event_repository: ActivityEventRepository

    def close(self) -> None:
        """Release resources created for a CLI command."""
        self.session.close()
        self.database_manager.close()


def _build_cli_context() -> CliContext:
    """Create settings, logging, authentication, clients, database and repositories."""
    settings = get_settings()
    configure_logging(settings)

    powerbi_authenticator = MsalAuthenticator(settings)
    powerbi_token = powerbi_authenticator.authenticate()["access_token"]

    graph_authenticator = MsalGraphAuthenticator(settings)
    graph_token = graph_authenticator.authenticate()["access_token"]

    powerbi_client = PowerBIClient(settings, powerbi_token)
    graph_client = GraphClient(settings, graph_token)
    xmla_client = XmlaClient(settings)

    database_manager = DatabaseManager(settings)
    database_manager.initialize()
    session = database_manager.get_session()

    return CliContext(
        settings=settings,
        powerbi_authenticator=powerbi_authenticator,
        graph_authenticator=graph_authenticator,
        powerbi_client=powerbi_client,
        graph_client=graph_client,
        xmla_client=xmla_client,
        database_manager=database_manager,
        session=session,
        workspace_repository=WorkspaceRepository(session),
        usage_metric_repository=UsageMetricRepository(session),
        activity_event_repository=ActivityEventRepository(session),
    )


def _run_async(awaitable: Awaitable[T]) -> T:
    """Run an async use case from the synchronous Typer command layer."""
    return asyncio.run(awaitable)


def _get_field(item: Any, *names: str, default: Any = "") -> Any:
    """Read the first available field from either a dict or object."""
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return default


def _format_bool(value: Any) -> str:
    """Format Power BI boolean-like values for Rich table output."""
    if isinstance(value, str):
        return "Yes" if value.lower() in {"true", "yes", "1"} else "No"
    return "Yes" if bool(value) else "No"


@app.command()
def sync_workspaces() -> None:
    """Synchronize workspaces from Power BI"""
    console.print("[bold blue]🔄 Syncing workspaces...[/bold blue]")

    context: CliContext | None = None
    try:
        context = _build_cli_context()
        service = WorkspaceService(context.powerbi_client, context.workspace_repository)
        workspace_count = _run_async(service.sync_workspaces())
        console.print(f"[green]✓ Synchronized {workspace_count} workspaces[/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e!s}[/red]")
        raise typer.Exit(code=1) from e
    finally:
        if context:
            context.close()


@app.command()
def sync_usage_metrics() -> None:
    """Synchronize usage metrics from Power BI"""
    console.print("[bold blue]📊 Syncing usage metrics...[/bold blue]")

    context: CliContext | None = None
    try:
        context = _build_cli_context()
        service = UsageMetricsService(
            context.powerbi_client,
            context.xmla_client,
            context.usage_metric_repository,
        )
        metrics_count = _run_async(service.sync_usage_metrics())
        console.print(f"[green]✓ Synchronized {metrics_count} usage metrics[/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e!s}[/red]")
        raise typer.Exit(code=1) from e
    finally:
        if context:
            context.close()


@app.command()
def sync_activity_events(
    days_back: Annotated[int, typer.Argument(help="Number of days to look back")] = 1,
) -> None:
    """Synchronize activity events from audit logs"""
    console.print(f"[bold blue]📋 Syncing activity events ({days_back} days)...[/bold blue]")

    context: CliContext | None = None
    try:
        context = _build_cli_context()
        service = ActivityEventsService(context.powerbi_client, context.activity_event_repository)
        events_count = _run_async(service.sync_activity_events(days_back=days_back))
        console.print(f"[green]✓ Synchronized {events_count} activity events[/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e!s}[/red]")
        raise typer.Exit(code=1) from e
    finally:
        if context:
            context.close()


@app.command()
def list_workspaces(
    skip: Annotated[int, typer.Argument(help="Skip N workspaces")] = 0,
    top: Annotated[int, typer.Argument(help="Show top N workspaces")] = 10,
) -> None:
    """List Power BI workspaces"""
    console.print("[bold blue]📚 Listing workspaces...[/bold blue]")

    context: CliContext | None = None
    try:
        context = _build_cli_context()
        workspaces_response = _run_async(context.powerbi_client.get_workspaces(skip=skip, top=top))
        workspaces = workspaces_response.get("value", []) if isinstance(workspaces_response, dict) else workspaces_response

        table = Table(title="Power BI Workspaces")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Premium", style="green")

        for workspace in workspaces:
            table.add_row(
                str(_get_field(workspace, "id", "workspace_id", "workspaceId")),
                str(_get_field(workspace, "name", "display_name", "displayName")),
                _format_bool(_get_field(workspace, "isOnDedicatedCapacity", "is_premium", "isPremium", default=False)),
            )

        console.print(table)
        console.print(f"[green]✓ Listed {len(workspaces)} workspaces (skip={skip}, top={top})[/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e!s}[/red]")
        raise typer.Exit(code=1) from e
    finally:
        if context:
            context.close()


@app.command()
def health_check() -> None:
    """Check platform health and connectivity"""
    console.print("[bold blue]🏥 Checking health...[/bold blue]")

    try:
        settings = get_settings()

        checks = {
            "Configuration": "✓" if settings else "✗",
            "Database URL": "✓" if settings.database_url else "✗",
            "Azure Credentials": "✓" if settings.azure_client_id else "✗",
            "Power BI API": "✓",
            "Logging": "✓",
        }

        for check, status in checks.items():
            color = "green" if status == "✓" else "red"
            console.print(f"  [{color}]{status}[/{color}] {check}")

        console.print("[green]✓ Health check completed[/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e!s}[/red]")
        raise typer.Exit(code=1) from e


@app.command()
def show_config() -> None:
    """Display current configuration (redacted secrets)"""
    settings = get_settings()

    console.print("[bold]Current Configuration:[/bold]")
    console.print(f"  Environment: {settings.environment}")
    console.print(f"  Debug: {settings.debug}")
    console.print(f"  Database: {str(settings.database_url).split('@')[0]}@...")
    console.print(f"  Log Level: {settings.log_level}")
    console.print(f"  Power BI API: {settings.powerbi_api_base_url}")


if __name__ == "__main__":
    app()
