"""
CLI entry point for Typer application
"""

import sys

# Rich console output uses emoji (checkmarks, status dots, etc.). Windows consoles
# default to a legacy codepage (e.g. cp1252) that can't encode them, which crashes
# every command with UnicodeEncodeError before it prints anything.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from powerbi_governance.interfaces.cli import app


if __name__ == "__main__":
    app()
