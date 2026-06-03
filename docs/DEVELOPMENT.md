# Development Guide

## Local Development Setup

### Quick Start

```bash
# Clone repository
git clone <repo-url>
cd powerbi-governance

# Install dependencies
poetry install --with dev

# Setup environment
cp .env.example .env

# Configure your credentials in .env
# AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, etc.

# Initialize database
poetry run alembic upgrade head

# Run health check
poetry run pbi-governance health-check
```

### IDE Configuration

#### VS Code

Install extensions:
- Python (Microsoft)
- Pylance
- Black Formatter
- Ruff (astral-sh)

Settings (`.vscode/settings.json`):
```json
{
    "[python]": {
        "editor.defaultFormatter": "ms-python.python",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": false,
    "python.linting.enabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ]
}
```

#### PyCharm

1. Open project
2. Configure Python interpreter: Poetry virtual env
3. Mark `src` as Sources Root
4. Mark `tests` as Tests Root

## Workflow

### Making Code Changes

1. **Create feature branch:**
   ```bash
   git checkout -b feature/workspace-sync-improvements
   ```

2. **Make changes with tests:**
   ```bash
   # Write test first (TDD)
   # Write implementation
   # Ensure tests pass
   poetry run pytest
   ```

3. **Format and lint:**
   ```bash
   # Auto-fix issues
   poetry run ruff check --fix src/ tests/
   
   # Check formatting
   poetry run black --check src/ tests/
   ```

4. **Type checking:**
   ```bash
   poetry run mypy src/powerbi_governance
   ```

5. **Run all checks:**
   ```bash
   poetry run pytest
   poetry run ruff check .
   poetry run mypy src/powerbi_governance
   ```

6. **Commit with pre-commit hooks:**
   ```bash
   git add .
   git commit -m "feat: add workspace sync improvements"
   ```

### Adding Dependencies

```bash
# Production dependency
poetry add pydantic-extra-types

# Development dependency
poetry add --group dev pytest-asyncio

# Lock and update
poetry lock --no-update
```

## Testing

### Writing Tests

#### Unit Test Example

```python
import pytest
from powerbi_governance.core.security import mask_secret

@pytest.mark.unit
class TestSecurityUtils:
    def test_mask_secret(self):
        result = mask_secret("supersecret", visible_chars=3)
        assert result == "sup*******"
        assert "supersecret" not in result
```

#### Integration Test Example

```python
import pytest
from powerbi_governance.infrastructure.auth import MsalAuthenticator

@pytest.mark.integration
@pytest.mark.skip(reason="Requires Azure credentials")
class TestAuthentication:
    @pytest.fixture
    def auth(self):
        return MsalAuthenticator()
    
    def test_authenticate(self, auth):
        token = auth.authenticate()
        assert "access_token" in token
```

### Test Fixtures

Use factories from `tests/fixtures/`:

```python
from tests.fixtures import UserFactory, WorkspaceFactory

def test_user_creation():
    user = UserFactory.create(email="test@example.com")
    assert user.email == "test@example.com"
```

### Running Tests

```bash
# All tests
poetry run pytest

# Specific file
poetry run pytest tests/unit/test_core.py

# Specific class
poetry run pytest tests/unit/test_core.py::TestSettings

# Specific test
poetry run pytest tests/unit/test_core.py::TestSettings::test_settings_default_values

# With coverage
poetry run pytest --cov=src/powerbi_governance --cov-report=html

# Only unit tests
poetry run pytest -m unit

# Only integration tests
poetry run pytest -m integration

# Fail fast on first error
poetry run pytest -x

# Show print statements
poetry run pytest -s

# Run in parallel
poetry run pytest -n auto
```

## Code Organization

### Naming Conventions

- **Modules:** lowercase with underscores
- **Classes:** PascalCase
- **Functions:** lowercase with underscores
- **Constants:** UPPER_CASE
- **Private:** prefix with underscore `_private`

### Import Order

```python
# 1. Standard library
import asyncio
from typing import Optional

# 2. Third-party
import structlog
from pydantic import BaseModel

# 3. Local
from powerbi_governance.core import get_settings
from powerbi_governance.domain.entities import User
```

### Docstring Format

```python
def mask_secret(secret: Optional[str], visible_chars: int = 4) -> str:
    """
    Mask a secret for safe logging.
    
    Shows only the first N characters, masking the rest with asterisks.
    
    Args:
        secret: Secret string to mask
        visible_chars: Number of characters to show at the beginning
        
    Returns:
        Masked secret string
        
    Example:
        >>> mask_secret("my_super_secret", visible_chars=3)
        'my_*****'
    """
    if not secret:
        return "***"
    return secret[:visible_chars] + "*" * (len(secret) - visible_chars)
```

## Debugging

### Print Debugging

```python
import structlog
log = structlog.get_logger(__name__)

# Instead of print
log.debug("Debug information", variable=value, status="checking")
```

### Using Debugger

```bash
# Run with debugger
poetry run python -m ipdb -m powerbi_governance.main

# Or use pdb breakpoints
import pdb; pdb.set_trace()
```

### Logging from Tests

```bash
# Show logs during tests
poetry run pytest -s

# Set log level
poetry run pytest --log-cli-level=DEBUG
```

## Adding New Features

### Checklist

1. ✅ Create domain entity/schema (if needed)
2. ✅ Add database model (if needed)
3. ✅ Implement repository
4. ✅ Create service with business logic
5. ✅ Add CLI command or API endpoint
6. ✅ Write unit tests (minimum 80% coverage)
7. ✅ Add integration tests
8. ✅ Update documentation
9. ✅ Add migration (if database changes)
10. ✅ Create PR with changelog

### Example: Add New Service

#### 1. Define Domain Entity

```python
# src/powerbi_governance/domain/entities/__init__.py
class LicenseAssignment(BaseEntity):
    """Power BI license assignment"""
    user_id: str
    license_type: str
    assigned_at: datetime
```

#### 2. Create Schema

```python
# src/powerbi_governance/domain/schemas/__init__.py
class LicenseAssignmentSchema(BaseSchema):
    """Schema for license assignment"""
    user_id: str
    license_type: str
```

#### 3. Add ORM Model

```python
# src/powerbi_governance/infrastructure/database/models.py
class LicenseAssignmentModel(Base):
    __tablename__ = "license_assignments"
    user_id = String(255)
    license_type = String(50)
```

#### 4. Implement Repository

```python
# src/powerbi_governance/infrastructure/repositories/__init__.py
class LicenseRepository(BaseRepository[T]):
    def get_by_user(self, user_id: str) -> Optional[T]:
        pass
```

#### 5. Create Service

```python
# src/powerbi_governance/application/services/__init__.py
class LicenseService:
    def __init__(self, graph_client, repository):
        self.graph_client = graph_client
        self.repository = repository
    
    async def sync_licenses(self) -> int:
        """Sync license assignments from Azure AD"""
        log.info("Syncing licenses")
        # Implementation
        return count
```

#### 6. Add CLI Command

```python
# src/powerbi_governance/interfaces/cli/__init__.py
@app.command()
def sync_licenses() -> None:
    """Synchronize license assignments"""
    console.print("Syncing licenses...")
    # Implementation
```

#### 7. Write Tests

```python
# tests/unit/test_licenses.py
@pytest.mark.unit
def test_license_sync():
    service = LicenseService(mock_client, mock_repo)
    count = asyncio.run(service.sync_licenses())
    assert count > 0
```

## Performance Optimization

### Database Queries

```python
# ❌ N+1 queries
for workspace in workspaces:
    print(workspace.datasets)  # Separate query per workspace

# ✅ Use eager loading
from sqlalchemy.orm import joinedload
workspaces = session.query(Workspace).options(
    joinedload(Workspace.datasets)
).all()
```

### API Calls

```python
# ❌ Sequential requests
for workspace_id in workspace_ids:
    datasets = await client.get_datasets(workspace_id)

# ✅ Concurrent requests
tasks = [client.get_datasets(wid) for wid in workspace_ids]
results = await asyncio.gather(*tasks)
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(param: str) -> dict:
    # Only computed once per unique param
    return result
```

## Release Process

### Version Bumping

```bash
# Bump patch version (0.1.0 → 0.1.1)
poetry version patch

# Bump minor version (0.1.0 → 0.2.0)
poetry version minor

# Bump major version (0.1.0 → 1.0.0)
poetry version major
```

### Publishing

```bash
# Build distribution
poetry build

# Publish to PyPI (configure credentials first)
poetry publish
```

## Contributing Guidelines

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Run all quality checks
5. Submit PR with:
   - Description of changes
   - Related issue links
   - Screenshots (if UI related)
   - Updated documentation

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

Examples:
```
feat(workspace): add workspace sync job
fix(auth): handle token expiration correctly
docs(setup): update installation guide
refactor(database): simplify session management
test(core): add settings validation tests
```

## Useful Commands

```bash
# Format all code
poetry run ruff check --fix .

# Check all
poetry run pytest && poetry run ruff check . && poetry run mypy src/

# Generate coverage report
poetry run pytest --cov=src/powerbi_governance --cov-report=html

# Open coverage report
open htmlcov/index.html

# Check for security vulnerabilities
poetry run pip-audit

# Generate dependency tree
poetry show --tree
```

## Resources

- [Python Documentation](https://docs.python.org/3.12/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Structlog Documentation](https://www.structlog.org/)
- [Typer Documentation](https://typer.tiangolo.com/)
