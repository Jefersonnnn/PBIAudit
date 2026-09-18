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
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from sqlalchemy.orm import Session

from powerbi_governance.application.services import (
    ActivityEventsService,
    LicenseService,
    UsageMetricsService,
    WorkspaceService,
)
from powerbi_governance.core import Settings, configure_logging, get_settings, mask_database_url
from powerbi_governance.infrastructure.auth import MsalAuthenticator, MsalGraphAuthenticator
from powerbi_governance.infrastructure.clients.graph import GraphClient
from powerbi_governance.infrastructure.clients.powerbi import PowerBIClient
from powerbi_governance.infrastructure.clients.xmla import XmlaClient
from powerbi_governance.infrastructure.database import DatabaseManager
from powerbi_governance.infrastructure.repositories import (
    ActivityEventRepository,
    LicenseAssignmentRepository,
    UsageMetricRepository,
    UserRepository,
    WorkspaceRepository,
)

log = structlog.get_logger(__name__)
console = Console()

T = TypeVar("T")

app = typer.Typer(
    name="pbi-governance",
    help="Power BI Governance Platform - Automated audit and analytics",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Power BI Governance Platform - Automated audit and analytics"""
    if ctx.invoked_subcommand is None:
        _run_interactive_menu()


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
    license_repository: LicenseAssignmentRepository
    user_repository: UserRepository

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
        license_repository=LicenseAssignmentRepository(session),
        user_repository=UserRepository(session),
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
    days_back: Annotated[int, typer.Argument(help="Number of days to look back (max 28)")] = 1,
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
def sync_licenses() -> None:
    """Synchronize Power BI license assignments from Microsoft Graph"""
    console.print("[bold blue]🔑 Syncing license assignments...[/bold blue]")

    context: CliContext | None = None
    try:
        context = _build_cli_context()
        service = LicenseService(context.graph_client, context.license_repository, context.user_repository)
        assignment_count = _run_async(service.sync_license_assignments())
        console.print(f"[green]✓ Synchronized {assignment_count} license assignments[/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e!s}[/red]")
        raise typer.Exit(code=1) from e
    finally:
        if context:
            context.close()


@app.command()
def license_report(
    inactive_days: Annotated[
        int, typer.Option(help="Days without activity before a license is flagged as idle")
    ] = 30,
) -> None:
    """
    Cross-reference Power BI licenses with actual usage to find idle/unused licenses.

    Reads from the local database, so run 'sync-licenses' and 'sync-activity-events'
    first (or on a schedule) to keep this report up to date.
    """
    console.print("[bold blue]🔍 Building license usage report...[/bold blue]")

    context: CliContext | None = None
    try:
        context = _build_cli_context()
        license_service = LicenseService(context.graph_client, context.license_repository, context.user_repository)

        activity_summary = context.activity_event_repository.get_usage_summary_by_user()
        rows = license_service.build_usage_report(activity_summary)

        if not rows:
            console.print(
                "[yellow]No license assignments found. Run 'sync-licenses' first "
                "(requires Graph User.Read.All and Organization.Read.All permissions).[/yellow]"
            )
            return

        table = Table(title="Power BI License Usage Audit")
        table.add_column("Name", style="magenta")
        table.add_column("Email", style="cyan")
        table.add_column("Cargo", style="white")
        table.add_column("Departamento", style="white")
        table.add_column("License", style="blue")
        table.add_column("Last Access", style="white")
        table.add_column("Idle (days)", justify="right")
        table.add_column("Dashboards Used", style="white")
        table.add_column("Status")

        idle_count = 0
        never_used_count = 0

        for row in rows:
            if row.last_access is None:
                status = "[red]● Never used[/red]"
                never_used_count += 1
                idle_count += 1
            elif row.days_since_access is not None and row.days_since_access >= inactive_days:
                status = "[yellow]● Idle[/yellow]"
                idle_count += 1
            else:
                status = "[green]● Active[/green]"

            dashboards_preview = ", ".join(row.resources[:3])
            if len(row.resources) > 3:
                dashboards_preview += f" (+{len(row.resources) - 3} more)"

            table.add_row(
                row.display_name,
                row.email,
                row.job_title or "-",
                row.department or "-",
                row.license_type,
                row.last_access.strftime("%Y-%m-%d") if row.last_access else "Never",
                str(row.days_since_access) if row.days_since_access is not None else "-",
                dashboards_preview or "-",
                status,
            )

        console.print(table)
        console.print(
            f"\n[bold]{len(rows)}[/bold] license(s) audited — "
            f"[yellow]{idle_count}[/yellow] idle (>{inactive_days}d or never used), "
            f"of which [red]{never_used_count}[/red] never accessed Power BI."
        )

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
    console.print(f"  Database: {mask_database_url(settings.database_url)}")
    console.print(f"  Log Level: {settings.log_level}")
    console.print(f"  Power BI API: {settings.powerbi_api_base_url}")


@dataclass
class _MenuAction:
    """One selectable entry in the interactive menu."""

    key: str
    label: str
    description: str
    run: Any


def _run_interactive_menu() -> None:
    """Show a numbered menu of commands so users don't have to remember/type them."""
    actions = [
        _MenuAction(
            "1",
            "Sincronizar licenças",
            "Busca no Microsoft Graph quem tem licença Power BI",
            sync_licenses,
        ),
        _MenuAction(
            "2",
            "Sincronizar eventos de atividade",
            "Busca no Power BI quem acessou o quê (máx. 28 dias)",
            lambda: sync_activity_events(
                IntPrompt.ask("Quantos dias sincronizar? (máx. 28)", default=7)
            ),
        ),
        _MenuAction(
            "3",
            "Relatório de uso de licenças",
            "Cruza licenças com atividade e aponta quem está ocioso",
            lambda: license_report(
                IntPrompt.ask("Considerar ociosa após quantos dias sem acesso?", default=30)
            ),
        ),
        _MenuAction(
            "4",
            "Sincronizar workspaces",
            "Descobre e atualiza os workspaces do Power BI",
            sync_workspaces,
        ),
        _MenuAction(
            "5",
            "Listar workspaces",
            "Lista os workspaces do Power BI direto da API",
            lambda: list_workspaces(
                0, IntPrompt.ask("Mostrar quantos workspaces?", default=10)
            ),
        ),
        _MenuAction(
            "6",
            "Verificar saúde da configuração",
            "Confere se as credenciais e o banco estão OK",
            health_check,
        ),
        _MenuAction(
            "7",
            "Ver configuração atual",
            "Mostra environment, banco (mascarado) e endpoints",
            show_config,
        ),
    ]
    choices = [action.key for action in actions] + ["0"]

    while True:
        console.print()
        console.print("[bold blue]Power BI Governance — Auditoria de Licenças[/bold blue]")
        console.print()

        menu = Table(show_header=False, box=None, padding=(0, 1))
        for action in actions:
            menu.add_row(f"[bold cyan]{action.key}[/bold cyan]", action.label, f"[dim]{action.description}[/dim]")
        menu.add_row("[bold cyan]0[/bold cyan]", "Sair", "")
        console.print(menu)
        console.print()

        choice = Prompt.ask("Escolha uma opção", choices=choices, default="0", show_choices=False)
        if choice == "0":
            break

        console.print()
        selected = next(action for action in actions if action.key == choice)
        try:
            selected.run()
        except typer.Exit:
            pass  # the command already printed its own error; return to the menu

        console.print()
        console.rule(style="dim")


if __name__ == "__main__":
    app()
