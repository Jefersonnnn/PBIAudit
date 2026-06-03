# Migration Notes

This file tracks major architectural decisions and future plans.

## Completed (Phase 1)

✅ Project scaffolding and directory structure
✅ Poetry configuration with comprehensive dependencies
✅ Pydantic v2 configuration management
✅ Structured logging with Structlog
✅ SQLAlchemy ORM models and session management
✅ Alembic database migration setup
✅ Domain layer with entities and schemas
✅ MSAL authentication integration
✅ Power BI REST API client
✅ Microsoft Graph API client
✅ Repository pattern implementation
✅ Application services layer
✅ Typer CLI framework
✅ Test fixtures and factories
✅ Pytest configuration
✅ Security utilities
✅ Documentation (README, Architecture, Config)

## In Progress (Phase 2)

🔄 Complete service implementations
🔄 Database integration and persistence
🔄 CLI command implementations
🔄 Comprehensive test coverage

## Planned (Phase 3)

📋 FastAPI REST API endpoints
📋 Scheduled job execution (APScheduler or similar)
📋 WebSocket support for real-time updates
📋 Power BI dashboard integration
📋 Advanced analytics and ML features

## Architectural Decisions

### 1. Clean Architecture Approach
**Decision:** Organize code into Domain → Application → Infrastructure layers

**Rationale:** Maximizes testability, maintainability and decoupling. Future changes to persistence or external services don't affect business logic.

### 2. Async/Await Throughout
**Decision:** Use async/await for I/O operations

**Rationale:** Better resource utilization for external API calls. Python 3.12+ has excellent async support.

### 3. Pydantic v2 for Validation
**Decision:** Use Pydantic for all data validation and serialization

**Rationale:** Industry standard, excellent type hints, automatic OpenAPI schema generation for future API.

### 4. Repository Pattern for Data Access
**Decision:** Abstract data access through repositories

**Rationale:** Enables different persistence backends. Easier testing with mocks. Single responsibility principle.

### 5. Service Layer Orchestration
**Decision:** Put business logic in services, not repositories or models

**Rationale:** Keeps code organized and testable. Services can use multiple repositories and clients.

### 6. MSAL for Authentication
**Decision:** Use Microsoft Authentication Library directly

**Rationale:** Native Azure integration, supports Service Principal pattern, automatic token refresh.

### 7. Structured Logging
**Decision:** Use Structlog for JSON-formatted logging

**Rationale:** Machine-readable logs, easier debugging and monitoring, industry standard.

## Integration Points

### Phase 2 Considerations

1. **Database Integration:**
   - Implement concrete repository methods
   - Add SQLAlchemy relationships
   - Create index strategies
   - Setup connection pooling

2. **Background Jobs:**
   - APScheduler or Celery for scheduling
   - Error handling and retry logic
   - Job monitoring and logging
   - Result tracking

3. **Caching:**
   - Redis for distributed caching
   - Token cache implementation
   - Cache invalidation strategy

### Phase 3 Considerations

1. **REST API:**
   - FastAPI framework
   - OpenAPI/Swagger documentation
   - Authentication middleware
   - Rate limiting
   - CORS configuration

2. **WebSocket Support:**
   - Real-time status updates
   - Job progress tracking
   - Live metrics streaming

3. **Analytics:**
   - Aggregation queries
   - Trend analysis
   - ML-based anomaly detection

## Python Version Support

- **Target:** Python 3.12+
- **Minimum:** Python 3.12
- **Rationale:** Latest LTS version, better type hints, performance improvements

## Future Library Upgrades

- Pydantic v3 (when stable for SQLAlchemy 3)
- SQLAlchemy 2.1+ (async full support)
- Python 3.13+ as it becomes available

## Known Limitations

1. **XMLA Client:** PyADOMD integration pending (requires Windows/.NET)
2. **API:** REST API not yet implemented
3. **Caching:** Simple in-memory caching only, no distributed cache
4. **Scheduling:** No background job execution yet
5. **Monitoring:** Application Insights integration not implemented

## Testing Coverage Goals

- **Unit Tests:** 80%+ coverage
- **Integration Tests:** Key workflows
- **End-to-End:** CLI commands validation

## Performance Targets

- Database connection pool: 10-20 connections
- API timeout: 30 seconds
- Dataset refresh timeout: 60 seconds
- Workspace sync: < 5 seconds for 100 workspaces

## Security Roadmap

1. ✅ Environment-based secrets (Phase 1)
2. 📋 Azure Key Vault integration (Phase 2)
3. 📋 Managed identity support (Phase 2)
4. 📋 API authentication/authorization (Phase 3)
5. 📋 Role-based access control (Phase 3)

## Breaking Changes Policy

Given the pre-release status (0.1.0):
- No API stability guarantees
- Breaking changes allowed with minor version bump
- After 1.0.0 release, follow semantic versioning strictly

## Community & Support

- GitHub Issues for bug reports
- Discussion board for feature requests
- Documentation in `/docs` folder
- Example scripts in `/examples` (future)
