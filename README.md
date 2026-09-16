# PowerBI Governance Platform - Enterprise Power BI Audit & Analytics

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Poetry](https://img.shields.io/badge/Poetry-enabled-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Beta-orange.svg)

**Enterprise-grade Power BI governance, audit and analytics platform**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Architecture](#architecture) • [Development](#development)

</div>

---

## Overview

PowerBI Governance is a comprehensive platform for automated Power BI governance, audit and analytics. It provides:

- **Automated Workspace Discovery** - Real-time discovery of all Power BI workspaces
- **Usage Analytics** - Comprehensive usage metrics collection and analysis
- **Activity Auditing** - Complete audit trail of all Power BI activities
- **License Management** - License assignment tracking and optimization
- **User Analytics** - User activity tracking and inactivity identification
- **Historical Tracking** - Long-term trend analysis and historical data retention
- **Enterprise Integration** - Prepared for Power BI dashboards and automated reporting

## Features

### Core Capabilities

✅ **Workspace Management**
- Automated discovery of all workspaces
- Workspace metadata tracking
- Capacity utilization monitoring
- Premium capacity detection

✅ **Usage Metrics**
- Report view tracking
- User engagement metrics
- Dataset refresh history
- Performance metrics collection

✅ **Activity Auditing**
- Real-time activity logging
- User action tracking
- Resource modification history
- Compliance audit trails

✅ **User Analytics**
- Inactive user identification
- User activity patterns
- License utilization tracking
- User segmentation

✅ **Reporting & Analytics**
- Built-in analytics dashboards (future)
- Trend analysis
- Actionable insights
- Data export capabilities

### Architecture

**Enterprise-Ready Design:**

```
Clean Architecture Layers:
├── Domain Layer (Business Logic)
├── Application Layer (Use Cases & Services)
├── Infrastructure Layer (Data & External APIs)
├── Interface Layer (CLI & APIs)
└── Utilities & Jobs
```

**Technology Stack:**

- **Python 3.12+** - Modern Python with type hints
- **Poetry** - Dependency and project management
- **Pydantic v2** - Data validation and serialization
- **SQLAlchemy 2.0** - ORM and database abstraction
- **Alembic** - Database migrations
- **Structlog** - Structured logging
- **HTTPX** - Async HTTP client
- **Typer** - Modern CLI framework
- **Pytest** - Comprehensive testing
- **Ruff** - Fast Python linter
- **MyPy** - Static type checking

## Installation

### Prerequisites

- Python 3.12 or higher
- Poetry 1.7+
- PostgreSQL 12+ (or SQLite for development)
- Microsoft Azure AD Service Principal credentials
- Power BI Premium capacity (for XMLA features)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourorg/powerbi-governance.git
   cd powerbi-governance
   ```

2. **Install Poetry** (if not already installed)
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**
   ```bash
   poetry install
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure AD and Power BI credentials
   ```

5. **Initialize database**
   ```bash
   poetry run alembic upgrade head
   ```

6. **Verify installation**
   ```bash
   poetry run python -m powerbi_governance.main --help
   ```

## Usage

### CLI Commands

#### Sync Workspaces
```bash
poetry run pbi-governance sync-workspaces
```
Discovers and synchronizes all Power BI workspaces.

#### Sync Usage Metrics
```bash
poetry run pbi-governance sync-usage-metrics
```
Collects usage metrics for all reports.

#### Sync Activity Events
```bash
poetry run pbi-governance sync-activity-events --days-back 7
```
Collects activity events from the past 7 days.

#### List Workspaces
```bash
poetry run pbi-governance list-workspaces --top 20
```
Lists available workspaces with metadata.

#### Health Check
```bash
poetry run pbi-governance health-check
```
Verifies platform health and connectivity.

#### Sync License Assignments
```bash
poetry run pbi-governance sync-licenses
```
Reads every Azure AD user's Power BI-related Microsoft 365 licenses (Pro, Premium Per User, Free)
from Microsoft Graph and stores a fresh point-in-time snapshot.

#### License Usage Audit
```bash
poetry run pbi-governance sync-licenses
poetry run pbi-governance sync-activity-events 30
poetry run pbi-governance license-report --inactive-days 30
```
`license-report` reads the local database (populated by `sync-licenses` and
`sync-activity-events`) and cross-references licensed users with their actual Power BI activity to
show, per user: license type, last access, which dashboards/reports they used, and whether the
license looks idle or was never used — the report you'd use to reclaim unused seats out of a fixed
license pool. Run the two sync commands first (or on a schedule) to keep it current.

**Required Azure AD app permissions (application/admin-consent, not delegated):**
- `User.Read.All` — list users and their assigned license plans
- `Organization.Read.All` — resolve license SKU/service-plan names
- Power BI Admin API access for the service principal (Power BI Admin Portal → tenant settings →
  "Allow service principals to use Power BI Admin APIs") — needed for `sync-activity-events` /
  `license-report` to see who actually opened which reports.

Microsoft Graph reference (how the `assignedPlans`/`subscribedSkus` requests in
[`GraphClient`](src/powerbi_governance/infrastructure/clients/graph/__init__.py) work):
https://learn.microsoft.com/en-us/graph/overview?context=graph%2Fapi%2F1.0&view=graph-rest-1.0

### Python API

```python
from powerbi_governance.core import get_settings, configure_logging
from powerbi_governance.infrastructure.auth import MsalAuthenticator
from powerbi_governance.infrastructure.clients.powerbi import PowerBIClient
from powerbi_governance.application.services import WorkspaceService

# Setup
settings = get_settings()
configure_logging(settings)

# Authenticate
auth = MsalAuthenticator(settings)
token = auth.authenticate()["access_token"]

# Create clients
powerbi_client = PowerBIClient(settings, token)

# Use services
service = WorkspaceService(powerbi_client, repository)
workspace_count = await service.sync_workspaces()
```

## Architecture

### Layer Breakdown

#### Domain Layer (`src/powerbi_governance/domain/`)
- **Entities**: Core business objects (User, Workspace, Dataset, Report, etc.)
- **Schemas**: Pydantic models for validation and serialization
- **Enums**: Type-safe enumerations
- **Models**: Separation of concerns for future extensibility

#### Application Layer (`src/powerbi_governance/application/`)
- **Services**: Business logic orchestration
- **Use Cases**: Application entry points
- **DTOs**: Data transfer objects

#### Infrastructure Layer (`src/powerbi_governance/infrastructure/`)
- **Authentication**: MSAL integration and token management
- **Database**: SQLAlchemy ORM and session management
- **Repositories**: Repository pattern implementation
- **Clients**: External API clients (Power BI, Graph, XMLA)

#### Interface Layer (`src/powerbi_governance/interfaces/`)
- **CLI**: Typer-based command-line interface
- **API**: FastAPI (future) REST API

### Database Schema

The platform maintains comprehensive historical data:

- **users** - Azure AD users and their Power BI access
- **workspaces** - Power BI workspaces and metadata
- **datasets** - Power BI datasets and refresh history
- **reports** - Power BI reports and configuration
- **usage_metrics** - Historical usage data
- **activity_events** - Complete audit trail
- **license_assignments** - License tracking
- **refresh_history** - Dataset refresh history

## Configuration

### Environment Variables

```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db

# Azure/Microsoft 365
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# Power BI
POWERBI_ADMIN_API_ENABLED=true
POWERBI_TIMEOUT_SECONDS=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Sync Jobs
SYNC_WORKSPACES_ENABLED=true
SYNC_CRON_SCHEDULE=0 2 * * *
```

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
poetry install --with dev

# Setup pre-commit hooks
pre-commit install

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/powerbi_governance

# Code quality checks
poetry run ruff check .
poetry run mypy src/powerbi_governance

# Format code
poetry run black .
poetry run isort .
```

### Project Structure

```
PBIAudit/
├── src/
│   └── powerbi_governance/
│       ├── core/               # Configuration, logging, security
│       ├── domain/             # Business logic entities
│       ├── application/        # Services and use cases
│       ├── infrastructure/     # Data access, clients, auth
│       ├── interfaces/         # CLI and API
│       ├── jobs/               # Scheduled jobs
│       └── utils/              # Utilities
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test factories
├── migrations/                 # Alembic migrations
├── docs/                       # Documentation
├── pyproject.toml              # Poetry configuration
├── alembic.ini                 # Alembic config
└── .env.example                # Environment template
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/unit/test_core.py

# Run with markers
poetry run pytest -m unit
poetry run pytest -m integration

# Run with coverage report
poetry run pytest --cov=src/powerbi_governance --cov-report=html
```

### Code Quality

The project uses:

- **Ruff** - Fast linting and formatting
- **MyPy** - Static type checking
- **Black** - Code formatting (via Ruff)
- **isort** - Import organization
- **Pre-commit** - Automated quality checks

```bash
# Run all checks
poetry run ruff check .
poetry run mypy src/powerbi_governance
poetry run pytest

# Auto-fix issues
poetry run ruff check --fix .
```

## Database Migrations

### Create New Migration

```bash
poetry run alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
# Apply all pending migrations
poetry run alembic upgrade head

# Revert to specific revision
poetry run alembic downgrade -1
```

### View Migration Status

```bash
poetry run alembic current
poetry run alembic history
```

## Roadmap

### Phase 1 (Current)
- [x] Project structure and scaffolding
- [x] Core configuration and logging
- [x] Domain models and schemas
- [x] Database layer
- [x] Authentication (MSAL)
- [x] API clients (Power BI, Graph, XMLA)
- [ ] Complete service implementations
- [ ] Database integration

### Phase 2
- [ ] REST API (FastAPI)
- [ ] Scheduled job execution
- [ ] Complete CLI commands
- [ ] Comprehensive testing

### Phase 3
- [ ] Power BI dashboard integration
- [ ] Advanced analytics
- [ ] ML-based anomaly detection
- [ ] Performance optimization

## Security

### Best Practices

- ✅ Secrets only via environment variables
- ✅ No hardcoded credentials
- ✅ Token caching and refresh
- ✅ Retry policies for resilience
- ✅ Structured logging without secrets
- ✅ Prepared for Azure Key Vault integration

### Authentication

The platform uses Service Principal authentication with MSAL:

1. Service Principal credentials from Azure AD
2. Token acquisition with automatic refresh
3. Secure token caching
4. Credential rotation support

## Performance

### Optimization Strategies

- Connection pooling (configurable)
- Async/await for I/O operations
- Batch operations for bulk inserts
- Caching with TTL
- Indexed database queries
- Pagination support

## Contributing

### Code Style

- Follow PEP 8 with Black formatting
- Type hints required
- Docstrings for all public functions
- Comprehensive test coverage

### Pull Requests

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks
5. Submit PR with description

## Support

### Documentation

- [Architecture Guide](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Configuration Guide](docs/CONFIG.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

### Issues

Report bugs and request features on GitHub Issues.

## License

MIT License - see LICENSE file for details

## Authors

- Your Organization <devops@yourcompany.com>

---

<div align="center">

**[⬆ back to top](#powerbi-governance-platform)**

</div>
