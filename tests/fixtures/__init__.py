"""
Test fixtures and factories for unit and integration tests
"""

import pytest
from factory import Faker

from powerbi_governance.domain.entities import User, Workspace


class UserFactory:
    """Factory for creating test User entities"""

    @staticmethod
    def create(**kwargs):
        """Create a User instance"""
        data = {
            "user_id": kwargs.get("user_id", "00000000-0000-0000-0000-000000000001"),
            "email": kwargs.get("email", "user@example.com"),
            "display_name": kwargs.get("display_name", "Test User"),
            "is_admin": kwargs.get("is_admin", False),
            "is_active": kwargs.get("is_active", True),
        }
        return User(**data)


class WorkspaceFactory:
    """Factory for creating test Workspace entities"""

    @staticmethod
    def create(**kwargs):
        """Create a Workspace instance"""
        data = {
            "workspace_id": kwargs.get("workspace_id", "00000000-0000-0000-0000-000000000002"),
            "name": kwargs.get("name", "Test Workspace"),
            "description": kwargs.get("description", "Test workspace description"),
            "is_premium": kwargs.get("is_premium", False),
            "state": kwargs.get("state", "ACTIVE"),
        }
        return Workspace(**data)


@pytest.fixture
def test_user():
    """Fixture providing a test user"""
    return UserFactory.create()


@pytest.fixture
def test_workspace():
    """Fixture providing a test workspace"""
    return WorkspaceFactory.create()


__all__ = [
    "UserFactory",
    "WorkspaceFactory",
    "test_user",
    "test_workspace",
]
