<!-- Project Structure Documentation -->

# Project Structure Overview

This document provides a visual guide to the project structure and explains the purpose of each directory.

## Complete Directory Tree

```
PBIAudit/
├── 📄 pyproject.toml                          # Poetry project configuration
├── 📄 alembic.ini                             # Alembic database migration config
├── 📄 README.md                               # Project overview and quickstart
├── 📄 .env.example                            # Environment variables template
├── 📄 .gitignore                              # Git ignore rules
├── 📄 .pre-commit-config.yaml                 # Pre-commit hooks configuration
│
├── 📁 src/powerbi_governance/
│   ├── 📄 __init__.py                         # Package initialization
│   ├── 📄 main.py                             # Main application entry point
│   ├── 📄 cli.py                              # CLI entry point
│   │
│   ├── 📁 core/                               # Cross-cutting concerns
│   │   ├── 📄 __init__.py
│   │   ├── 📄 config.py                       # Settings management (Pydantic)
│   │   ├── 📄 logging.py                      # Structured logging setup
│   │   ├── 📄 constants.py                    # Application constants
│   │   └── 📄 security.py                     # Security utilities
│   │
│   ├── 📁 domain/                             # Business logic (Clean Architecture)
│   │   ├── 📄 __init__.py
│   │   ├── 📁 entities/                       # Domain entities
│   │   │   └── 📄 __init__.py                 # User, Workspace, Dataset, Report, etc.
│   │   ├── 📁 enums/                          # Type-safe enumerations
│   │   │   └── 📄 __init__.py                 # Status, Activity types, etc.
│   │   ├── 📁 schemas/                        # Pydantic validation schemas
│   │   │   └── 📄 __init__.py                 # DTOs for API/database
│   │   └── 📁 models/                         # Separation point for extensions
│   │       └── 📄 __init__.py
│   │
│   ├── 📁 application/                        # Business use cases
│   │   ├── 📄 __init__.py
│   │   ├── 📁 services/                       # Service layer
│   │   │   └── 📄 __init__.py                 # WorkspaceService, UsageMetricsService, etc.
│   │   ├── 📁 use_cases/                      # Use case orchestration (future)
│   │   │   └── 📄 __init__.py
│   │   └── 📁 dto/                            # Data transfer objects
│   │       └── 📄 __init__.py
│   │
│   ├── 📁 infrastructure/                     # Technical implementation
│   │   ├── 📄 __init__.py
│   │   ├── 📁 auth/                           # Authentication
│   │   │   └── 📄 __init__.py                 # MSAL integration
│   │   ├── 📁 database/                       # Data persistence
│   │   │   ├── 📄 __init__.py                 # DatabaseManager, session
│   │   │   └── 📄 models.py                   # SQLAlchemy ORM models
│   │   ├── 📁 repositories/                   # Repository pattern
│   │   │   └── 📄 __init__.py                 # Base + specific repositories
│   │   ├── 📁 clients/                        # External API clients
│   │   │   ├── 📁 powerbi/                    # Power BI REST API
│   │   │   │   └── 📄 __init__.py
│   │   │   ├── 📁 graph/                      # Microsoft Graph API
│   │   │   │   └── 📄 __init__.py
│   │   │   └── 📁 xmla/                       # XMLA/Analysis Services
│   │   │       └── 📄 __init__.py
│   │   └── 📁 storage/                        # Future storage implementations
│   │       └── 📄 __init__.py
│   │
│   ├── 📁 interfaces/                        # External interfaces
│   │   ├── 📄 __init__.py
│   │   ├── 📁 cli/                            # Typer CLI
│   │   │   └── 📄 __init__.py                 # Commands: sync, list, health-check
│   │   └── 📁 api/                            # FastAPI (future)
│   │       └── 📄 __init__.py
│   │
│   ├── 📁 jobs/                               # Scheduled jobs
│   │   └── 📄 __init__.py                     # WorkspaceSyncJob, UsageMetricsSyncJob, etc.
│   │
│   └── 📁 utils/                              # Utilities & helpers
│       └── 📄 __init__.py                     # Date handling, list chunking, email masking
│
├── 📁 tests/                                  # Test suite
│   ├── 📄 __init__.py
│   ├── 📄 conftest.py                         # Pytest configuration
│   ├── 📁 unit/                               # Unit tests (isolated)
│   │   └── 📄 test_core.py                    # Config, security, entities
│   ├── 📁 integration/                        # Integration tests
│   │   └── 📄 test_integration.py             # Cross-component tests
│   └── 📁 fixtures/                           # Test factories & fixtures
│       └── 📄 __init__.py                     # UserFactory, WorkspaceFactory, etc.
│
├── 📁 migrations/                             # Alembic migrations
│   ├── 📄 env.py                              # Alembic environment setup
│   ├── 📄 script.py.mako                      # Migration template
│   ├── 📁 versions/                           # Migration history
│   │   └── 📄 001_initial_schema.py           # Initial tables
│   └── 📄 alembic_version                     # Current migration version
│
├── 📁 docs/                                   # Documentation
│   ├── 📄 ARCHITECTURE.md                     # Architecture guide
│   ├── 📄 CONFIG.md                           # Configuration guide
│   ├── 📄 DEVELOPMENT.md                      # Development guide
│   ├── 📄 API.md                              # API reference (planned)
│   ├── 📄 ROADMAP.md                          # Project roadmap
│   └── 📄 EXAMPLES.py                         # Usage examples
│
└── 📁 logs/                                   # Application logs (generated)
    └── 📄 powerbi_governance.log              # Main log file
```

## Layer Description

### Core Layer (`core/`)
- Configuration management
- Logging setup
- Security utilities
- Application constants

### Domain Layer (`domain/`)
**No external dependencies**
- Business entities
- Validation schemas
- Type enumerations
- Pure business logic

### Application Layer (`application/`)
**Depends on:** Domain, Infrastructure
- Services orchestrating business logic
- Use case implementations
- DTOs for data transfer

### Infrastructure Layer (`infrastructure/`)
**Depends on:** Domain, Core
- Database access (SQLAlchemy)
- External API clients
- Authentication (MSAL)
- Repository implementations

### Interface Layer (`interfaces/`)
**Depends on:** Application, Infrastructure, Domain
- CLI commands (Typer)
- REST API endpoints (FastAPI, future)
- Entry points

## Key Design Principles

1. **Inward Dependencies**: Outer layers depend on inner layers, never reverse
2. **Domain-Driven**: Business logic lives in domain and application layers
3. **Repository Pattern**: Data access abstracted through repositories
4. **Separation of Concerns**: Each layer has single, well-defined responsibility
5. **Testability**: Each layer can be tested independently with mocks

## Adding New Features

1. Define entity in `domain/entities/`
2. Create schema in `domain/schemas/`
3. Add ORM model in `infrastructure/database/models.py`
4. Implement repository in `infrastructure/repositories/`
5. Create service in `application/services/`
6. Add CLI command in `interfaces/cli/`
7. Write tests in `tests/`

## Import Paths

```python
# Correct imports (downward dependencies)
from powerbi_governance.core import get_settings
from powerbi_governance.domain.entities import Workspace
from powerbi_governance.application.services import WorkspaceService
from powerbi_governance.infrastructure.clients.powerbi import PowerBIClient
from powerbi_governance.interfaces.cli import app

# Never do this (upward dependencies)
# from powerbi_governance.interfaces import something_from_application
```

## Configuration Files

- **pyproject.toml**: Poetry dependencies, tool configurations
- **alembic.ini**: Database migration settings
- **.env.example**: Environment variable template
- **.pre-commit-config.yaml**: Code quality hooks
- **pytest.ini** (in pyproject.toml): Test configuration

## Development Workflow

```
Make change → Run tests → Format code → Lint → Type check → Commit
  ✏️         → 🧪        → 🎨        → 🔍   → ✓         → ✅
```

## Production Deployment

```
Package → Build distribution → Publish → Deploy
  📦    →      🏗️            →    📤   →   🚀
```

See [DEVELOPMENT.md](DEVELOPMENT.md) and [CONFIG.md](CONFIG.md) for detailed workflows.
