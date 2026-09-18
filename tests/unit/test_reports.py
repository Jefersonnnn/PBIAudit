"""Unit tests for the HTML license usage report renderer."""

from datetime import datetime, timedelta

import pytest

from powerbi_governance.application.services import DepartmentUsageSummary, LicenseUsageRow
from powerbi_governance.interfaces.reports import render_license_usage_report
from powerbi_governance.interfaces.reports.gerencias import GerenciaMapping


def _row(**overrides) -> LicenseUsageRow:
    defaults = dict(
        display_name="Ana Souza",
        email="ana@example.com",
        license_type="Power BI Pro",
        is_account_enabled=True,
        last_access=None,
        days_since_access=None,
        resources=[],
        job_title="Analista",
        department="Financeiro",
    )
    defaults.update(overrides)
    return LicenseUsageRow(**defaults)


@pytest.mark.unit
class TestRenderLicenseUsageReport:
    def test_renders_department_user_and_dashboard_drill_down(self):
        rows = [
            _row(
                display_name="Ana Souza",
                email="ana@example.com",
                department="Financeiro",
                last_access=datetime.utcnow() - timedelta(days=1),
                days_since_access=1,
                resources=["Executive Dashboard", "Sales Dashboard"],
            ),
            _row(
                display_name="Bruno Lima",
                email="bruno@example.com",
                department="Financeiro",
                last_access=None,
                days_since_access=None,
                resources=[],
            ),
        ]
        summaries = [
            DepartmentUsageSummary(
                department="Financeiro", total_licenses=2, active_count=1, idle_count=1, never_used_count=1
            )
        ]

        html = render_license_usage_report(rows, summaries, inactive_days=30)

        assert "<!DOCTYPE html>" in html
        assert "Financeiro" in html
        assert "Ana Souza" in html and "ana@example.com" in html
        assert "Bruno Lima" in html and "bruno@example.com" in html
        assert "Executive Dashboard" in html
        assert "Sales Dashboard" in html
        assert "Nenhum dashboard acessado." in html  # Bruno never used any
        assert "2 licença(s)" in html

    def test_escapes_user_supplied_values(self):
        rows = [_row(display_name="<script>alert(1)</script>", resources=["<img src=x>"])]
        summaries = [
            DepartmentUsageSummary(
                department="Financeiro", total_licenses=1, active_count=0, idle_count=1, never_used_count=1
            )
        ]

        html = render_license_usage_report(rows, summaries, inactive_days=30)

        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        assert "<img src=x>" not in html

    def test_handles_no_department_bucket_and_empty_report(self):
        rows = [_row(department=None)]
        summaries = [
            DepartmentUsageSummary(
                department="Sem departamento", total_licenses=1, active_count=0, idle_count=1, never_used_count=1
            )
        ]

        html = render_license_usage_report(rows, summaries, inactive_days=30)
        assert "Sem departamento" in html

        empty_html = render_license_usage_report([], [], inactive_days=30)
        assert "Nenhuma licença encontrada." in empty_html
        assert "<!DOCTYPE html>" in empty_html

    def test_groups_departments_under_their_gerencia_code(self):
        """'034 CEM Coordenação Eletromecânica' -> Gerência 034 > department label without the code."""
        rows = [
            _row(
                display_name="Ana Souza",
                email="ana@example.com",
                department="034 CEM Coordenação Eletromecânica",
            ),
            _row(
                display_name="Bruno Lima",
                email="bruno@example.com",
                department="034 CEM Manutenção Mecânica",
            ),
        ]
        summaries = [
            DepartmentUsageSummary(
                department="034 CEM Coordenação Eletromecânica",
                total_licenses=1,
                active_count=0,
                idle_count=1,
                never_used_count=1,
            ),
            DepartmentUsageSummary(
                department="034 CEM Manutenção Mecânica",
                total_licenses=1,
                active_count=0,
                idle_count=1,
                never_used_count=1,
            ),
        ]

        html = render_license_usage_report(rows, summaries, inactive_days=30)

        assert "Gerência 034" in html
        assert "CEM Coordenação Eletromecânica" in html
        assert "CEM Manutenção Mecânica" in html
        # the gerência header aggregates both departments under it
        assert html.index("Gerência 034") < html.index("CEM Coordenação Eletromecânica")
        assert "2 licença(s)" in html  # gerência-level total across both departments

    def test_shows_gerencia_names_and_groups_aliased_departments_when_a_mapping_is_given(self):
        rows = [
            _row(display_name="Ana Souza", department="026 CIN Coordenação de Infraestrutura de TI"),
            _row(display_name="Bruno Lima", email="bruno@example.com", department="GTI"),
        ]
        summaries = [
            DepartmentUsageSummary("026 CIN Coordenação de Infraestrutura de TI", 1, 0, 1, 1),
            DepartmentUsageSummary("GTI", 1, 0, 1, 1),
        ]
        mapping = GerenciaMapping(names={"026": "Gerência de TI"}, aliases={"gti": "026"})

        html = render_license_usage_report(rows, summaries, inactive_days=30, gerencia_mapping=mapping)

        assert "026 · Gerência de TI" in html
        assert "Gerência 026 · Gerência" not in html  # the name already says "Gerência", so it isn't repeated
        assert "Sem gerência" not in html  # the aliased "GTI" joined gerência 026
        assert html.count('<details class="gerencia"') == 1
        assert "2 licença(s)" in html

    def test_gerencia_name_not_starting_with_gerencia_is_prefixed_with_it(self):
        rows = [_row(department="034 CEM Coordenação")]
        summaries = [DepartmentUsageSummary("034 CEM Coordenação", 1, 0, 1, 1)]
        mapping = GerenciaMapping(names={"034": "Manutenção"})

        html = render_license_usage_report(rows, summaries, inactive_days=30, gerencia_mapping=mapping)

        assert "Gerência 034 · Manutenção" in html

    def test_gerencia_without_a_name_in_the_mapping_shows_only_its_code(self):
        rows = [_row(department="034 CEM Coordenação")]
        summaries = [DepartmentUsageSummary("034 CEM Coordenação", 1, 0, 1, 1)]
        mapping = GerenciaMapping(names={"026": "Gerência de TI"})

        html = render_license_usage_report(rows, summaries, inactive_days=30, gerencia_mapping=mapping)

        assert "Gerência 034<" in html
        assert "·" not in html.split("<main>")[1]

    def test_department_without_a_leading_code_falls_back_to_sem_gerencia(self):
        rows = [_row(department="Financeiro")]
        summaries = [
            DepartmentUsageSummary(
                department="Financeiro", total_licenses=1, active_count=0, idle_count=1, never_used_count=1
            )
        ]

        html = render_license_usage_report(rows, summaries, inactive_days=30)

        assert "Sem gerência" in html
        assert "Financeiro" in html
