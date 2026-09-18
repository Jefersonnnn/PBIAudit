"""Unit tests for gerência name mapping (gerencias.csv) and template generation."""

import pytest

from powerbi_governance.interfaces.reports.gerencias import (
    UNKNOWN_GERENCIA,
    GerenciaMapping,
    build_gerencia_template_rows,
    load_gerencia_mapping,
    normalize_code,
    write_gerencia_template,
)


@pytest.mark.unit
class TestGerenciaMapping:
    def test_split_parses_leading_code_and_falls_back(self):
        mapping = GerenciaMapping()

        assert mapping.split("034 CEM Coordenação Eletromecanica") == ("034", "CEM Coordenação Eletromecanica")
        assert mapping.split("Financeiro") == (UNKNOWN_GERENCIA, "Financeiro")

    def test_split_uses_aliases_case_insensitively_for_departments_without_code(self):
        mapping = GerenciaMapping(aliases={"gti": "026"})

        assert mapping.split("GTI") == ("026", "GTI")
        assert mapping.split("gti") == ("026", "gti")

    def test_normalize_code_restores_leading_zeros_dropped_by_excel(self):
        assert normalize_code("34") == "034"
        assert normalize_code(" 034 ") == "034"
        assert normalize_code("ABC") == "ABC"


@pytest.mark.unit
class TestLoadGerenciaMapping:
    def test_loads_semicolon_csv_with_bom_names_and_aliases(self, tmp_path):
        path = tmp_path / "gerencias.csv"
        path.write_text(
            "codigo;nome;apelidos;dica;usuarios\n"
            "034;Gerência de Manutenção de Sistemas;;GMS;108\n"
            "026;Gerência de TI;GTI|TI|Tecnologia da Informação;GTI;31\n"
            "999;;;;1\n",
            encoding="utf-8-sig",
        )

        mapping = load_gerencia_mapping(path)

        assert mapping.names == {"034": "Gerência de Manutenção de Sistemas", "026": "Gerência de TI"}
        assert mapping.split("Tecnologia da Informação") == ("026", "Tecnologia da Informação")
        assert mapping.split("ti")[0] == "026"

    def test_loads_comma_csv_and_pads_codes_saved_without_leading_zeros(self, tmp_path):
        path = tmp_path / "gerencias.csv"
        path.write_text("codigo,nome\n34,Manutenção\n", encoding="utf-8")

        assert load_gerencia_mapping(path).names == {"034": "Manutenção"}

    def test_rejects_a_file_without_the_expected_columns(self, tmp_path):
        path = tmp_path / "gerencias.csv"
        path.write_text("a;b\n1;2\n", encoding="utf-8")

        with pytest.raises(ValueError, match="codigo"):
            load_gerencia_mapping(path)

    def test_empty_file_yields_an_empty_mapping(self, tmp_path):
        path = tmp_path / "gerencias.csv"
        path.write_text("", encoding="utf-8")

        assert load_gerencia_mapping(path) == GerenciaMapping()


@pytest.mark.unit
class TestGerenciaTemplate:
    def test_builds_one_row_per_code_with_manager_hint_and_lists_departments_without_code(self):
        counts = {
            "034 CEM Coordenação Eletromecanica": 16,
            "034 GMS Gerente": 1,
            "034 CMR Coordenação de Manutenção de Redes e Ramais": 36,
            "050 ETE Jarivatuba": 43,
            "GTI": 1,
        }

        rows, without_code = build_gerencia_template_rows(counts)

        assert without_code == ["GTI"]
        assert [row["codigo"] for row in rows] == ["034", "050"]
        assert rows[0]["dica"] == "GMS"
        assert rows[0]["usuarios"] == "53"
        assert rows[0]["nome"] == ""
        assert rows[1]["dica"] == ""

    def test_written_template_round_trips_through_the_loader(self, tmp_path):
        rows, _ = build_gerencia_template_rows({"034 GMS Gerente": 1})
        rows[0]["nome"] = "Gerência de Manutenção"
        path = tmp_path / "gerencias.csv"

        write_gerencia_template(path, rows)

        assert load_gerencia_mapping(path).names == {"034": "Gerência de Manutenção"}
