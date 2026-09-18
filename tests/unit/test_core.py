"""
Unit tests - tests for individual components in isolation
"""

import pytest
from pydantic import PostgresDsn, TypeAdapter

from powerbi_governance.core.config import Settings, get_settings
from powerbi_governance.core.security import mask_database_url, mask_secret, is_valid_uuid
from tests.fixtures import UserFactory, WorkspaceFactory


@pytest.mark.unit
class TestSettings:
    """Tests for Settings configuration"""

    def test_settings_default_values(self):
        """Test that settings load with default values"""
        settings = Settings()
        assert settings.environment is not None
        assert settings.database_pool_size > 0

    def test_settings_singleton(self):
        """Test that get_settings returns cached instance"""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_is_production(self):
        """Test is_production property"""
        settings = Settings(environment="production")
        assert settings.is_production is True

    def test_is_development(self):
        """Test is_development property"""
        settings = Settings(environment="development")
        assert settings.is_development is True


@pytest.mark.unit
class TestSecurityUtils:
    """Tests for security utilities"""

    def test_mask_secret_short(self):
        """Test masking short secrets"""
        result = mask_secret("abc", visible_chars=2)
        assert result == "ab*"

    def test_mask_secret_empty(self):
        """Test masking empty/None secrets"""
        assert mask_secret(None) == "***"
        assert mask_secret("") == "***"

    def test_mask_database_url_hides_password(self):
        """The password must never appear in the masked output, unlike a naive '@' split."""
        url = TypeAdapter(PostgresDsn).validate_python(
            "postgresql+psycopg2://myuser:mysecretpass@dbhost.example:5432/mydb"
        )

        masked = mask_database_url(url)

        assert "mysecretpass" not in masked
        assert masked == "postgresql+psycopg2://myuser:***@dbhost.example:5432/mydb"

    def test_mask_database_url_handles_missing_credentials(self):
        """A URL without a password shouldn't render a stray ':***'."""
        url = TypeAdapter(PostgresDsn).validate_python("postgresql://dbhost.example:5432/mydb")

        assert mask_database_url(url) == "postgresql://dbhost.example:5432/mydb"

    def test_is_valid_uuid(self):
        """Test UUID validation"""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        invalid_uuid = "not-a-uuid"

        assert is_valid_uuid(valid_uuid) is True
        assert is_valid_uuid(invalid_uuid) is False


@pytest.mark.unit
class TestDomainEntities:
    """Tests for domain entities"""

    def test_user_creation(self):
        """Test User entity creation"""
        user = UserFactory.create(email="test@example.com")
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_workspace_creation(self):
        """Test Workspace entity creation"""
        workspace = WorkspaceFactory.create(name="Analytics")
        assert workspace.name == "Analytics"
        assert workspace.state == "ACTIVE"

    def test_entity_timestamps(self):
        """Test entity timestamp generation"""
        user = UserFactory.create()
        assert user.created_at is not None
        assert user.updated_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
