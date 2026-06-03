# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffolding and complete directory structure
- Clean Architecture implementation with 7 layers
- Poetry configuration with comprehensive dependencies
- Pydantic v2 settings management
- Structured logging with Structlog
- SQLAlchemy ORM and Alembic migrations
- MSAL authentication integration
- Power BI REST API client
- Microsoft Graph API client
- XMLA/Analysis Services client (placeholder)
- Repository pattern for data access
- Service layer for business logic
- Typer CLI framework with initial commands
- Test infrastructure with pytest, fixtures and factories
- Security utilities and secret masking
- Database models for core entities:
  - Users
  - Workspaces
  - Datasets
  - Reports
  - Usage Metrics
  - Activity Events
- Comprehensive documentation:
  - Architecture guide
  - Configuration guide
  - Development guide
  - API reference (planned)
  - Project roadmap
  - Project structure documentation

### Planned (Phase 2)
- Complete service implementations
- Database repository implementations
- CLI command implementations
- REST API (FastAPI)
- Background job scheduling
- Comprehensive test coverage

### Planned (Phase 3)
- WebSocket support
- Advanced analytics
- ML-based anomaly detection
- Power BI dashboard integration

## [0.1.0] - 2024-01-XX

### Initial Release

Initial release with core scaffolding and foundational architecture.

**Status:** Beta - API subject to change
