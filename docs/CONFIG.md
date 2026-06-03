# Configuration Guide

## Environment Setup

### 1. Install Python 3.12+

```bash
# Windows (using Python installer)
# Download from https://www.python.org/downloads/

# macOS (using Homebrew)
brew install python@3.12

# Linux (Ubuntu/Debian)
sudo apt-get install python3.12 python3.12-venv
```

### 2. Install Poetry

```bash
# Official installation
curl -sSL https://install.python-poetry.org | python3 -

# Or using Homebrew (macOS)
brew install poetry

# Or using pipx
pip install pipx
pipx install poetry
```

### 3. Clone and Setup Repository

```bash
git clone https://github.com/yourorg/powerbi-governance.git
cd powerbi-governance

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

## Environment Variables

Create a `.env` file in the project root with the following configuration:

### Database Configuration

```bash
# PostgreSQL (Production)
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/powerbi_governance

# SQLite (Development)
DATABASE_URL=sqlite:///./powerbi_governance.db

# Connection pool settings
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_RECYCLE=3600
```

### Azure Authentication

```bash
# Get these from Azure Portal
AZURE_TENANT_ID=your-tenant-id.onmicrosoft.com
AZURE_CLIENT_ID=00000000-0000-0000-0000-000000000000
AZURE_CLIENT_SECRET=your-service-principal-secret
```

**How to create Service Principal:**
1. Go to Azure Portal → App registrations
2. Click "New registration"
3. Name: "PowerBI Governance"
4. Create Client Secret
5. Grant admin consent for:
   - Power BI Service: admin and user scopes
   - Microsoft Graph: User.Read, Group.Read

### Power BI Configuration

```bash
# API Endpoints
POWERBI_API_BASE_URL=https://api.powerbi.com/v1.0/myorg
GRAPH_API_BASE_URL=https://graph.microsoft.com/v1.0

# Admin APIs (requires admin role)
POWERBI_ADMIN_API_ENABLED=true
POWERBI_TIMEOUT_SECONDS=30

# XMLA for DAX queries
XMLA_ENDPOINT_ENABLED=true
XMLA_TIMEOUT_SECONDS=60
```

### Application Configuration

```bash
# Environment
ENVIRONMENT=development  # or production, testing
DEBUG=false

# Logging
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json         # json or text
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/powerbi_governance.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

### Sync Jobs Configuration

```bash
# Enable specific sync jobs
SYNC_WORKSPACES_ENABLED=true
SYNC_USAGE_METRICS_ENABLED=true
SYNC_ACTIVITY_EVENTS_ENABLED=true

# Cron schedule (default: 2 AM daily)
SYNC_CRON_SCHEDULE=0 2 * * *
```

### Retry Policy

```bash
# Automatic retry configuration
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2
RETRY_INITIAL_DELAY=1
```

### Caching

```bash
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
```

### Azure Key Vault (Optional)

```bash
# Future support for secrets management
AZURE_KEYVAULT_ENABLED=false
AZURE_KEYVAULT_URL=https://your-vault.vault.azure.net/
```

## Database Setup

### PostgreSQL

```bash
# Create database and user
sudo -u postgres psql

CREATE USER powerbi_user WITH PASSWORD 'password';
CREATE DATABASE powerbi_governance OWNER powerbi_user;
GRANT ALL PRIVILEGES ON DATABASE powerbi_governance TO powerbi_user;
```

### SQLite (Development)

SQLite is automatically created by SQLAlchemy on first run.

### Run Migrations

```bash
# Apply all migrations
poetry run alembic upgrade head

# Create specific revision
poetry run alembic revision --autogenerate -m "Description"

# Check status
poetry run alembic current
poetry run alembic history
```

## Microsoft Graph Permissions

The Service Principal requires these permissions:

1. **Power BI Service Connector:**
   - Workspace.Read.All
   - Report.Read.All
   - Dataset.Read.All
   - Activity.Read.All (Admin)

2. **Microsoft Graph:**
   - User.Read.All
   - Directory.Read.All
   - Organization.Read.All

### Grant Admin Consent

```bash
# In Azure Portal:
# 1. Go to App registrations → Your app
# 2. API Permissions
# 3. Click "Grant admin consent for [Tenant]"
```

## Pre-commit Hooks

Enable automated code quality checks:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files

# Skip hooks for a commit
git commit --no-verify
```

## Development Tools

### Code Formatting

```bash
# Format with Black
poetry run black src/ tests/

# Sort imports
poetry run isort src/ tests/

# Both together
poetry run ruff check --fix src/ tests/
```

### Linting

```bash
# Check with Ruff
poetry run ruff check src/

# Check types
poetry run mypy src/powerbi_governance
```

### Testing

```bash
# Run all tests
poetry run pytest

# With coverage
poetry run pytest --cov=src/powerbi_governance

# Specific test file
poetry run pytest tests/unit/test_core.py

# With markers
poetry run pytest -m unit
poetry run pytest -m integration
```

## Running the Application

### CLI Commands

```bash
# Show help
poetry run pbi-governance --help

# Sync workspaces
poetry run pbi-governance sync-workspaces

# Sync usage metrics
poetry run pbi-governance sync-usage-metrics

# Sync activity events
poetry run pbi-governance sync-activity-events --days-back 7

# List workspaces
poetry run pbi-governance list-workspaces --top 20

# Check health
poetry run pbi-governance health-check

# Show configuration
poetry run pbi-governance show-config
```

### Python Script

```bash
poetry run python -m powerbi_governance.main
```

## Docker Setup

### Build Image

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy files
COPY pyproject.toml poetry.lock ./
COPY src/ ./src/

# Install dependencies
RUN poetry install --no-dev

# Run application
CMD ["poetry", "run", "pbi-governance"]
```

### Build and Run

```bash
docker build -t powerbi-governance:latest .
docker run --env-file .env powerbi-governance:latest
```

## Production Deployment

### Best Practices

1. **Secrets Management:**
   - Use Azure Key Vault
   - Never commit .env files
   - Rotate credentials regularly

2. **Database:**
   - Use managed PostgreSQL
   - Enable SSL/TLS
   - Regular backups

3. **Monitoring:**
   - Application Insights
   - Log aggregation
   - Performance metrics

4. **Security:**
   - Enable Azure AD authentication
   - Use service principal with minimal permissions
   - Audit all access

### CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install poetry
      - run: poetry install
      - run: poetry run pytest
      - run: poetry run ruff check .
      - run: poetry run mypy src/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      # Deploy to production
```

## Troubleshooting

### Common Issues

**Issue:** `ModuleNotFoundError: No module named 'powerbi_governance'`

*Solution:* Ensure src is in PYTHONPATH or run via Poetry:
```bash
poetry run python -m powerbi_governance.main
```

**Issue:** Database connection refused

*Solution:* Check PostgreSQL is running and credentials are correct:
```bash
psql -U powerbi_user -d powerbi_governance
```

**Issue:** Authentication failed

*Solution:* Verify Azure credentials:
```bash
# Check tenant ID format (should be GUID or .onmicrosoft.com)
# Verify Service Principal has required permissions
# Ensure client secret hasn't expired
```

**Issue:** Power BI API returns 401

*Solution:* Token may have expired:
```python
# Token is automatically refreshed
# If issue persists, check:
# 1. Credentials in .env
# 2. Service Principal permissions
# 3. Power BI admin role assignment
```

## Support

For configuration issues, check:
- [Environment Variables Guide](#environment-variables)
- [Logs](#logging) (check logs/ directory)
- GitHub Issues
- Documentation in `/docs`
