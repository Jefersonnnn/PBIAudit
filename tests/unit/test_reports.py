"""Unit tests for the HTML license usage report renderer."""

from datetime import datetime, timedelta

import pytest

from powerbi_governance.application.services import DepartmentUsageSummary, LicenseUsageRow
from powerbi_governance.interfaces.reports import render_license_usage_report


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
