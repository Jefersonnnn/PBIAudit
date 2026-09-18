# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- `sync-licenses`/`license-report`/`department-report` now track only Power BI Pro
  (`BI_AZURE_P1`/`BI_AZURE_P2`) instead of every Power BI-related plan. Power BI (Free) doesn't
  consume a seat from the tenant's fixed pool, and Premium/Premium Per User are licensed
  separately, so both were cluttering the audit with licenses that aren't relevant to reclaiming
  Pro seats.
- Removed `datasets` and `reports` tables/models/repositories - nothing ever wrote to them (no
  command persisted a `Dataset`/`Report` row), so they only added dead schema. Migration 003 drops
  both tables.
- `sync-usage-metrics` now actually persists usage metrics. `UsageMetricRepository` was a stub
  (every method was `pass`) that silently discarded everything while the CLI reported success.
- `sync-licenses` now also upserts each user's profile (display name, job title, department) into
  `users`, and `license-report` shows job title/department per row - migration 003 adds those two
  columns.

### Added
- `department-report` CLI command: same license-vs-usage data as `license-report`, aggregated by
  department (active/idle/never-used counts and idle percentage per team) instead of per user.
- License usage audit: `sync-licenses` and `license-report` CLI commands cross-reference Power
  BI-related Microsoft 365 license assignments (from Microsoft Graph `assignedPlans`) with
  persisted Power BI activity events, to find licensed users who never or rarely use Power BI
- `LicenseAssignment` domain entity, `license_assignments` table/migration and repository
- `LicenseService` (sync + report building) and `GraphClient.get_all_users_with_licenses` /
  `get_subscribed_skus`
- `ActivityEventRepository` now actually persists events and aggregates last access + distinct
  resources per user (was a stub that silently discarded every synced event)
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

### Security
- Removed a hardcoded database password that was checked into `core/config.py` as the default
  `database_url` value; it is now required to come from `.env`/the environment. **Rotate that
  database password**, since it was present in the committed source history.

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
