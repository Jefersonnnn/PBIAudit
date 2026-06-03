# Quick Start Guide

## Installation (5 minutes)

```bash
# 1. Clone repository
git clone <repo-url>
cd powerbi-governance

# 2. Install Python 3.12+ (if needed)
# Download from https://www.python.org/downloads/

# 3. Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 4. Install dependencies
poetry install

# 5. Configure environment
cp .env.example .env
# Edit .env with your Azure credentials

# 6. Initialize database
poetry run alembic upgrade head
```

## First Run

```bash
# Check installation
poetry run python -m powerbi_governance.cli health-check

# Show help
poetry run pbi-governance --help
```

## Common Commands

```bash
# Sync workspaces
poetry run pbi-governance sync-workspaces

# List workspaces
poetry run pbi-governance list-workspaces

# Sync metrics
poetry run pbi-governance sync-usage-metrics

# Check status
poetry run pbi-governance health-check
```

## Configuration

Set these environment variables in `.env`:

```bash
# Azure credentials (from Service Principal)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# Database (PostgreSQL or SQLite)
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/db

# Logging
LOG_LEVEL=INFO
```

See [Configuration Guide](docs/CONFIG.md) for full options.

## Next Steps

- Read [Architecture Guide](docs/ARCHITECTURE.md)
- Check [Development Guide](docs/DEVELOPMENT.md)
- Review [Examples](docs/EXAMPLES.py)
- Run tests: `poetry run pytest`

## Getting Help

- 📖 [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/yourorg/powerbi-governance/issues)
- 💬 [Discussions](https://github.com/yourorg/powerbi-governance/discussions)

---

**Ready to contribute?** See [Contributing Guide](CONTRIBUTING.md)
