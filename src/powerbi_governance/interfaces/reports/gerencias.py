"""
Gerência (management unit) names and department parsing for the HTML report.

Azure AD's `department` field encodes the gerência as a leading numeric code,
e.g. "034 CEM Coordenação Eletromecânica" -> gerência "034". Nothing in
Microsoft 365 maps that code to a name, so the names come from a CSV the user
maintains (`gerencias.csv`), with columns:

    codigo;nome;apelidos

`apelidos` is optional: a `|`-separated list of raw department values that have
no leading code but belong to that gerência (e.g. `GTI|TI|Tecnologia da Informação`).
Extra columns (such as the hints written by ``write_gerencia_template``) are ignored.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

UNKNOWN_GERENCIA = "Sem gerência"

_CODE_PATTERN = re.compile(r"^(\d{2,})\s+(.+)$")
_TEMPLATE_COLUMNS = ["codigo", "nome", "apelidos", "dica", "usuarios"]


def normalize_code(code: str) -> str:
    """Zero-pad numeric codes to 3 digits, since Excel drops leading zeros when saving CSVs."""
    code = code.strip()
    return code.zfill(3) if code.isdigit() else code


@dataclass
class GerenciaMapping:
    """Gerência names by code, plus aliases for departments that carry no leading code."""

    names: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)

    def split(self, raw_department: str) -> tuple[str, str]:
        """Split a raw department string into (gerência code, department label)."""
        raw = raw_department.strip()
        match = _CODE_PATTERN.match(raw)
        if match:
            code, label = match.groups()
            return normalize_code(code), label.strip() or raw_department
        alias_code = self.aliases.get(raw.casefold())
        if alias_code:
            return alias_code, raw_department
        return UNKNOWN_GERENCIA, raw_department

    def name_for(self, code: str) -> str | None:
        return self.names.get(code)


def load_gerencia_mapping(path: str | Path) -> GerenciaMapping:
    """Read a gerencias.csv (`,` or `;` delimited, UTF-8 with or without BOM)."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines:
        return GerenciaMapping()

    delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    reader = csv.DictReader(lines, delimiter=delimiter)
    headers = {(header or "").strip().casefold() for header in (reader.fieldnames or [])}
    if not {"codigo", "nome"} <= headers:
        raise ValueError(f"{path}: the header must contain the columns 'codigo' and 'nome'")

    mapping = GerenciaMapping()
    for row in reader:
        row = {(key or "").strip().casefold(): (value or "").strip() for key, value in row.items()}
        code = normalize_code(row.get("codigo", ""))
        if not code:
            continue
        if row.get("nome"):
            mapping.names[code] = row["nome"]
        for alias in filter(None, (a.strip() for a in row.get("apelidos", "").split("|"))):
            mapping.aliases[alias.casefold()] = code
    return mapping


def build_gerencia_template_rows(department_counts: dict[str, int]) -> tuple[list[dict[str, str]], list[str]]:
    """
    Build one template row per gerência code found in the given department values.

    Returns (rows, departments_without_code). Each row's `dica` is the acronym of
    the department whose text is "Gerente" (usually the gerência's own manager),
    a hint to help fill in the real name.
    """
    users_by_code: dict[str, int] = {}
    hint_by_code: dict[str, str] = {}
    without_code: list[str] = []

    for department, count in sorted(department_counts.items()):
        match = _CODE_PATTERN.match(department.strip())
        if not match:
            without_code.append(department)
            continue
        code = normalize_code(match.group(1))
        users_by_code[code] = users_by_code.get(code, 0) + count
        acronym, _, rest = match.group(2).partition(" ")
        if rest.strip().casefold() == "gerente":
            hint_by_code[code] = acronym

    rows = [
        {
            "codigo": code,
            "nome": "",
            "apelidos": "",
            "dica": hint_by_code.get(code, ""),
            "usuarios": str(users_by_code[code]),
        }
        for code in sorted(users_by_code)
    ]
    return rows, without_code


def write_gerencia_template(path: str | Path, rows: Iterable[dict[str, str]]) -> None:
    """Write the template as `;`-delimited UTF-8 with BOM, which opens correctly in Excel (pt-BR)."""
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_TEMPLATE_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
