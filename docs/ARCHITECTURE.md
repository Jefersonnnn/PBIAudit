# Architecture Guide

## Overview

PowerBI Governance follows **Clean Architecture** principles, separating concerns into distinct layers with clear dependencies flowing inward.

## Architectural Layers

### 1. Domain Layer
**Location:** `src/powerbi_governance/domain/`

Pure business logic with zero external dependencies.

- **Entities** - Core business objects (User, Workspace, Dataset, etc.)
- **Enums** - Type-safe enumerations
- **Schemas** - Pydantic models for validation
- **Models** - Future extensibility point

**Key Principle:** Domain layer knows nothing about databases, APIs, or frameworks.

### 2. Application Layer
**Location:** `src/powerbi_governance/application/`

Orchestrates domain logic to fulfill use cases.

- **Services** - Business logic orchestration
  - `WorkspaceService` - Workspace discovery and management
  - `UsageMetricsService` - Usage data collection
  - `ActivityEventsService` - Audit event collection
  - `UserService` - User analysis and tracking

- **Use Cases** - Application entry points (future)
- **DTOs** - Data transfer objects

**Key Principle:** Services use repositories and clients to fulfill business requirements.

### 3. Infrastructure Layer
**Location:** `src/powerbi_governance/infrastructure/`

Implements technical concerns and external integrations.

#### 3.1 Authentication (`auth/`)
- MSAL integration for Azure AD
- Service Principal authentication
- Token caching and refresh
- Multi-flow support (future)

#### 3.2 Database (`database/`)
- SQLAlchemy ORM models
- Database session management
- Connection pooling
- Database initialization

#### 3.3 Repositories (`repositories/`)
- Generic repository pattern
- Workspace, Dataset, Report, User repositories
- Query abstraction
- Pagination support

#### 3.4 Clients (`clients/`)
- **PowerBI Client** - Power BI REST API
- **Graph Client** - Microsoft Graph API
- **XMLA Client** - Analysis Services queries
- Retry policies and error handling

### 4. Interface Layer
**Location:** `src/powerbi_governance/interfaces/`

Presents application to external users.

- **CLI** (`cli/`) - Typer-based command interface
- **API** (`api/`) - FastAPI endpoints (future)

**Key Principle:** Multiple interfaces can use same application layer.

### 5. Core Layer
**Location:** `src/powerbi_governance/core/`

Cross-cutting concerns.

- **Config** - Settings management with Pydantic
- **Logging** - Structured logging with Structlog
- **Security** - Secret masking, validation
- **Constants** - Application constants

### 6. Jobs Layer
**Location:** `src/powerbi_governance/jobs/`

Scheduled background tasks.

- Workspace synchronization
- Usage metrics collection
- Activity events collection

### 7. Utils Layer
**Location:** `src/powerbi_governance/utils/`

Shared utilities and helpers.

## Dependency Graph

```
┌─────────────────────────────────────────┐
│         Interface Layer (CLI/API)       │
├─────────────────────────────────────────┤
│         Application Layer               │
│      (Services, Use Cases, DTOs)        │
├─────────────────────────────────────────┤
│      Infrastructure Layer               │
│   (Auth, DB, Repos, Clients, Jobs)     │
├─────────────────────────────────────────┤
│         Core Layer                      │
│   (Config, Logging, Security)           │
├─────────────────────────────────────────┤
│         Domain Layer                    │
│   (Entities, Schemas, Models, Enums)   │
└─────────────────────────────────────────┘
```

**Rule:** Dependencies always point inward. Higher layers depend on lower layers, never the reverse.

## Design Patterns

### 1. Repository Pattern
```python
class BaseRepository(Generic[T]):
    def get_by_id(self, id: str) -> Optional[T]: ...
    def get_all(self, skip: int, limit: int) -> List[T]: ...
    def create(self, entity: T) -> T: ...
    def update(self, id: str, entity: T) -> Optional[T]: ...
    def delete(self, id: str) -> bool: ...
```

**Benefit:** Abstracts data access, enabling multiple persistence implementations.

### 2. Service Layer
```python
class WorkspaceService:
    def __init__(self, powerbi_client, repository):
        self.powerbi_client = powerbi_client
        self.repository = repository
    
    async def sync_workspaces(self) -> int:
        # Orchestrate domain logic
        pass
```

**Benefit:** Centralizes business logic, reusable across interfaces.

### 3. Dependency Injection
Services receive dependencies via constructor, enabling:
- Easy testing with mocks
- Flexible configuration
- Loose coupling

### 4. Factory Pattern
Test factories create domain objects:
```python
user = UserFactory.create(email="test@example.com")
```

**Benefit:** Consistent test data generation.

## Data Flow

### Synchronization Flow

```
CLI Command
    ↓
Interface Layer (Typer)
    ↓
Application Layer (Service)
    ↓
Infrastructure Layer
    ├── PowerBI Client (REST API)
    ├── Authentication (MSAL)
    ├── Repository (Storage)
    └── Database (SQLAlchemy)
    ↓
Domain Layer (Entity Creation)
    ↓
Database Persistence
```

### Query Flow

```
CLI List Command
    ↓
Interface Layer
    ↓
Application Layer (Service)
    ↓
Repository.get_all()
    ↓
Database Query
    ↓
Entity Mapping
    ↓
Schema Serialization
    ↓
CLI Display
```

## Configuration Management

### Settings Priority
1. Environment variables (highest priority)
2. .env file
3. Defaults in Settings class

### Example
```python
from powerbi_governance.core import get_settings

settings = get_settings()  # Cached singleton
print(settings.database_url)
print(settings.log_level)
```

## Logging Architecture

### Structured Logging
```python
import structlog
log = structlog.get_logger(__name__)

log.info(
    "workspace_synced",
    workspace_id="123",
    count=45,
    duration_seconds=2.5
)
```

### Outputs
- **JSON format** for production (machine-readable)
- **Console format** for development (human-readable)
- **File output** with rotation
- **Multiple handlers** for flexibility

## Testing Strategy

### Unit Tests
- Test individual functions/classes
- Mock external dependencies
- Fast execution
- High coverage

### Integration Tests
- Test component interactions
- Use real database (SQLite for tests)
- Skip external API tests
- Slower but realistic

### Test Structure
```
tests/
├── unit/
│   └── test_core.py         # Config, security, etc.
├── integration/
│   └── test_integration.py  # Full workflows
└── fixtures/
    └── __init__.py          # Factories and fixtures
```

## Extension Points

### Add New Domain Entity
1. Define Entity in `domain/entities/`
2. Create Schema in `domain/schemas/`
3. Add ORM Model in `infrastructure/database/models.py`
4. Implement Repository
5. Create Service with business logic
6. Add CLI commands or API endpoints

### Add New API Client
1. Create new file in `infrastructure/clients/`
2. Implement client class with retry logic
3. Add to services as dependency
4. Use in application layer

### Add New Data Source
1. Create repository implementation
2. Implement in infrastructure layer
3. Use in services
4. Expose through CLI/API

## Performance Considerations

### Database
- Connection pooling (10 connections default)
- Query indexing
- Batch operations
- Pagination for large datasets

### APIs
- Async/await for I/O
- Request timeout configuration
- Retry policy with exponential backoff
- Rate limiting awareness

### Caching
- Token caching for authentication
- Optional TTL-based caching
- Cache invalidation strategy

## Security Architecture

### Authentication
- Service Principal flow via MSAL
- Automatic token refresh
- Secure token storage (environment)
- No credential logging

### Data Protection
- Secret masking in logs
- Connection string sanitization
- Future: Azure Key Vault integration

### API Security
- Bearer token validation (future)
- Role-based access control (future)
- Audit logging for all operations

## Future Architecture Enhancements

1. **Event-Driven Architecture**
   - Message queues (Azure Service Bus)
   - Event handlers for background tasks

2. **Caching Layer**
   - Redis for distributed caching
   - Cache invalidation strategies

3. **API Gateway**
   - Rate limiting
   - Authentication/Authorization
   - Request/Response logging

4. **Async Task Queue**
   - Celery or similar
   - Background job scheduling
   - Result tracking

5. **Monitoring & Observability**
   - Application Insights integration
   - Distributed tracing
   - Performance metrics
