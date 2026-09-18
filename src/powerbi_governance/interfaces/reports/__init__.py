"""
HTML rendering for the license usage audit report.

Produces a single self-contained HTML file (no external assets) with a
gerência -> department -> user -> dashboard drill-down, using native
<details>/<summary> elements so no JavaScript is needed.
"""

from __future__ import annotations

import html as html_module
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional

from powerbi_governance.application.services import DepartmentUsageSummary, LicenseUsageRow
from powerbi_governance.interfaces.reports.gerencias import UNKNOWN_GERENCIA, GerenciaMapping

_UNKNOWN_DEPARTMENT = "Sem departamento"


@dataclass
class _GerenciaGroup:
    """One gerência (management unit), aggregated from the departments under it."""

    code: str
    name: Optional[str] = None
    departments: list[DepartmentUsageSummary] = field(default_factory=list)

    @property
    def total_licenses(self) -> int:
        return sum(department.total_licenses for department in self.departments)

    @property
    def active_count(self) -> int:
        return sum(department.active_count for department in self.departments)

    @property
    def idle_count(self) -> int:
        return sum(department.idle_count for department in self.departments)

    @property
    def never_used_count(self) -> int:
        return sum(department.never_used_count for department in self.departments)

    @property
    def idle_percentage(self) -> float:
        return (self.idle_count / self.total_licenses * 100) if self.total_licenses else 0.0

    @property
    def label(self) -> str:
        if self.code == UNKNOWN_GERENCIA:
            return self.code
        if not self.name:
            return f"Gerência {self.code}"
        if self.name.casefold().startswith(("gerência", "gerencia")):
            return f"{self.code} · {self.name}"
        return f"Gerência {self.code} · {self.name}"


def _group_by_gerencia(
    department_summaries: list[DepartmentUsageSummary], mapping: GerenciaMapping
) -> list[_GerenciaGroup]:
    """Group department summaries by their gerência code (parsed, or via a mapping alias)."""
    groups: dict[str, _GerenciaGroup] = {}
    for summary in department_summaries:
        code, _ = mapping.split(summary.department)
        group = groups.setdefault(code, _GerenciaGroup(code=code, name=mapping.name_for(code)))
        group.departments.append(summary)

    for group in groups.values():
        group.departments.sort(key=lambda d: (d.idle_percentage, d.total_licenses), reverse=True)

    return sorted(groups.values(), key=lambda g: (g.idle_percentage, g.total_licenses), reverse=True)


def _escape(value: object) -> str:
    """HTML-escape a value, treating None as an empty string."""
    return html_module.escape(str(value)) if value is not None else ""


def _status_label_and_class(row: LicenseUsageRow, inactive_days: int) -> tuple[str, str]:
    """Return the (label, CSS class) pair describing a license row's usage status."""
    if row.last_access is None:
        return "Nunca usada", "status-never"
    if row.days_since_access is not None and row.days_since_access >= inactive_days:
        return "Ociosa", "status-idle"
    return "Ativa", "status-active"


def _render_dashboards(resources: list[str]) -> str:
    """Render the list of dashboards/reports a user has accessed."""
    if not resources:
        return '<p class="empty">Nenhum dashboard acessado.</p>'
    items = "".join(f"<li>{_escape(resource)}</li>" for resource in resources)
    return f'<ul class="dashboard-list">{items}</ul>'


def _render_user(row: LicenseUsageRow, inactive_days: int) -> str:
    """Render one drill-down <details> block for a single licensed user."""
    label, css_class = _status_label_and_class(row, inactive_days)
    last_access = row.last_access.strftime("%d/%m/%Y") if row.last_access else "Nunca"
    idle_days = str(row.days_since_access) if row.days_since_access is not None else "-"

    return f"""
        <details class="user">
          <summary>
            <span class="chevron"></span>
            <span class="user-name">{_escape(row.display_name)}</span>
            <span class="user-email">{_escape(row.email)}</span>
            <span class="badge {css_class}">{label}</span>
          </summary>
          <div class="user-body">
            <dl>
              <dt>Cargo</dt><dd>{_escape(row.job_title or "-")}</dd>
              <dt>Licença</dt><dd>{_escape(row.license_type)}</dd>
              <dt>Último acesso</dt><dd>{_escape(last_access)}</dd>
              <dt>Dias sem acesso</dt><dd>{_escape(idle_days)}</dd>
            </dl>
            <h4>Dashboards utilizados</h4>
            {_render_dashboards(row.resources)}
          </div>
        </details>
    """


def _render_department(
    summary: DepartmentUsageSummary,
    rows: list[LicenseUsageRow],
    inactive_days: int,
    mapping: GerenciaMapping,
) -> str:
    """Render one drill-down <details> block for a department and its users."""
    _, label = mapping.split(summary.department)
    sorted_rows = sorted(
        rows, key=lambda row: (row.days_since_access is None, row.days_since_access or 0), reverse=True
    )
    users_html = "".join(_render_user(row, inactive_days) for row in sorted_rows)

    return f"""
      <details class="department" open>
        <summary>
          <span class="chevron"></span>
          <span class="dept-name">{_escape(label)}</span>
          <span class="dept-stats">
            <span class="dept-total">{summary.total_licenses} licença(s)</span>
            <span class="badge status-active">{summary.active_count} ativa(s)</span>
            <span class="badge status-idle">{summary.idle_count} ociosa(s)</span>
            <span class="badge status-never">{summary.never_used_count} nunca usada(s)</span>
            <span class="dept-pct">{summary.idle_percentage:.0f}% ociosa</span>
          </span>
        </summary>
        <div class="department-body">
          {users_html}
        </div>
      </details>
    """


def _render_gerencia(
    group: _GerenciaGroup,
    rows_by_department: dict[str, list[LicenseUsageRow]],
    inactive_days: int,
    mapping: GerenciaMapping,
) -> str:
    """Render one drill-down <details> block for a gerência and its departments."""
    departments_html = "".join(
        _render_department(summary, rows_by_department.get(summary.department, []), inactive_days, mapping)
        for summary in group.departments
    )

    return f"""
      <details class="gerencia" open>
        <summary>
          <span class="chevron"></span>
          <span class="gerencia-name">{_escape(group.label)}</span>
          <span class="dept-stats">
            <span class="dept-total">{group.total_licenses} licença(s)</span>
            <span class="badge status-active">{group.active_count} ativa(s)</span>
            <span class="badge status-idle">{group.idle_count} ociosa(s)</span>
            <span class="badge status-never">{group.never_used_count} nunca usada(s)</span>
            <span class="dept-pct">{group.idle_percentage:.0f}% ociosa</span>
          </span>
        </summary>
        <div class="gerencia-body">
          {departments_html}
        </div>
      </details>
    """


def render_license_usage_report(
    rows: Iterable[LicenseUsageRow],
    department_summaries: Iterable[DepartmentUsageSummary],
    *,
    inactive_days: int,
    generated_at: Optional[datetime] = None,
    gerencia_mapping: Optional[GerenciaMapping] = None,
) -> str:
    """
    Render a standalone HTML license usage audit report.

    Gerências (management units, parsed from the leading numeric code Azure AD
    puts on the department field, e.g. "034 CEM Coordenação Eletromecânica")
    are listed first, each expandable to its departments, each department
    expandable to its users, each user expandable to the dashboards they
    accessed. Reuses the same rows/summaries as the `license-report` and
    `department-report` CLI commands, so the numbers always match.

    Args:
        rows: Per-user rows from ``LicenseService.build_usage_report``
        department_summaries: Per-department summaries from
            ``LicenseService.summarize_by_department``
        inactive_days: Days without activity before a license is flagged as idle
        generated_at: Timestamp to display as the report's generation time
            (defaults to now)
        gerencia_mapping: Optional gerência names (and aliases for departments
            with no leading code), loaded from gerencias.csv. Without it,
            gerências show only their numeric code.

    Returns:
        A complete, self-contained HTML document (no external assets)
    """
    rows = list(rows)
    department_summaries = list(department_summaries)
    generated_at = generated_at or datetime.utcnow()

    rows_by_department: dict[str, list[LicenseUsageRow]] = {}
    for row in rows:
        rows_by_department.setdefault(row.department or _UNKNOWN_DEPARTMENT, []).append(row)

    total_licenses = sum(summary.total_licenses for summary in department_summaries)
    total_active = sum(summary.active_count for summary in department_summaries)
    total_idle = sum(summary.idle_count for summary in department_summaries)
    total_never_used = sum(summary.never_used_count for summary in department_summaries)

    mapping = gerencia_mapping or GerenciaMapping()
    gerencia_groups = _group_by_gerencia(department_summaries, mapping)
    gerencias_html = "".join(
        _render_gerencia(group, rows_by_department, inactive_days, mapping) for group in gerencia_groups
    )

    if not department_summaries:
        gerencias_html = '<p class="empty">Nenhuma licença encontrada.</p>'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auditoria de Uso de Licenças Power BI</title>
<style>
{_STYLE}
</style>
</head>
<body>
  <header>
    <h1>Auditoria de Uso de Licenças Power BI</h1>
    <p class="subtitle">
      Gerado em {generated_at.strftime("%d/%m/%Y %H:%M")} UTC ·
      licença considerada ociosa após {inactive_days}+ dias sem acesso
    </p>
  </header>

  <section class="summary-cards">
    <div class="card">
      <span class="card-value">{total_licenses}</span>
      <span class="card-label">Licenças Pro</span>
    </div>
    <div class="card card-active">
      <span class="card-value">{total_active}</span>
      <span class="card-label">Ativas</span>
    </div>
    <div class="card card-idle">
      <span class="card-value">{total_idle}</span>
      <span class="card-label">Ociosas</span>
    </div>
    <div class="card card-never">
      <span class="card-value">{total_never_used}</span>
      <span class="card-label">Nunca usadas</span>
    </div>
  </section>

  <main>
    {gerencias_html}
  </main>

  <footer>
    <p>PBIAudit &middot; Relatório gerado automaticamente a partir de sync-licenses e sync-activity-events</p>
  </footer>
</body>
</html>
"""


_STYLE = """
  :root {
    --bg: #f5f6fa;
    --card-bg: #ffffff;
    --text: #1f2430;
    --muted: #6b7280;
    --border: #e5e7eb;
    --accent: #2563eb;
    --green: #16a34a;
    --green-bg: #dcfce7;
    --amber: #b45309;
    --amber-bg: #fef3c7;
    --red: #dc2626;
    --red-bg: #fee2e2;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 32px 24px 64px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  header { max-width: 960px; margin: 0 auto 24px; }
  h1 { margin: 0 0 4px; font-size: 24px; }
  .subtitle { margin: 0; color: var(--muted); font-size: 14px; }
  main { max-width: 960px; margin: 0 auto; }
  footer { max-width: 960px; margin: 32px auto 0; color: var(--muted); font-size: 12px; text-align: center; }

  .summary-cards {
    max-width: 960px;
    margin: 0 auto 24px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
  .card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
  }
  .card-value { display: block; font-size: 28px; font-weight: 700; }
  .card-label { display: block; margin-top: 4px; color: var(--muted); font-size: 13px; }
  .card-active .card-value { color: var(--green); }
  .card-idle .card-value { color: var(--amber); }
  .card-never .card-value { color: var(--red); }

  details.gerencia {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 12px;
    overflow: hidden;
  }
  details.gerencia > summary {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding: 16px 20px;
    cursor: pointer;
    list-style: none;
  }
  details.gerencia > summary::-webkit-details-marker { display: none; }
  .gerencia-name { font-weight: 700; font-size: 17px; margin-right: auto; }
  .gerencia-body { padding: 4px 20px 16px; border-top: 1px solid var(--border); }

  details.department {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    margin: 10px 0;
    overflow: hidden;
  }
  details.department > summary {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding: 12px 16px;
    cursor: pointer;
    list-style: none;
  }
  details.department > summary::-webkit-details-marker { display: none; }
  .dept-name { font-weight: 600; font-size: 14px; margin-right: auto; }
  .dept-stats { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13px; }
  .dept-total { color: var(--muted); }
  .dept-pct { font-weight: 600; }
  .department-body { padding: 4px 16px 12px; border-top: 1px solid var(--border); background: var(--card-bg); }

  details.user {
    border-top: 1px solid var(--border);
    padding: 2px 0;
  }
  details.user:first-child { border-top: none; }
  details.user > summary {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 4px;
    cursor: pointer;
    list-style: none;
  }
  details.user > summary::-webkit-details-marker { display: none; }
  .user-name { font-weight: 600; }
  .user-email { color: var(--muted); font-size: 13px; margin-right: auto; }
  .user-body { padding: 4px 4px 14px 24px; }
  .user-body dl { display: grid; grid-template-columns: 140px 1fr; gap: 4px 12px; margin: 0 0 12px; font-size: 13px; }
  .user-body dt { color: var(--muted); }
  .user-body dd { margin: 0; }
  .user-body h4 { margin: 0 0 6px; font-size: 13px; color: var(--muted); font-weight: 600; }
  .dashboard-list { margin: 0; padding-left: 18px; font-size: 13px; }
  .dashboard-list li { margin-bottom: 2px; }
  .empty { color: var(--muted); font-size: 13px; font-style: italic; margin: 0; }

  .chevron {
    width: 8px;
    height: 8px;
    border-right: 2px solid var(--muted);
    border-bottom: 2px solid var(--muted);
    transform: rotate(-45deg);
    transition: transform 0.15s ease;
    flex-shrink: 0;
  }
  details[open] > summary .chevron { transform: rotate(45deg); }

  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }
  .status-active, .badge.status-active { color: var(--green); background: var(--green-bg); }
  .status-idle, .badge.status-idle { color: var(--amber); background: var(--amber-bg); }
  .status-never, .badge.status-never { color: var(--red); background: var(--red-bg); }

  @media (max-width: 640px) {
    .summary-cards { grid-template-columns: repeat(2, 1fr); }
    .user-body dl { grid-template-columns: 1fr; }
  }
"""


__all__ = ["render_license_usage_report"]
