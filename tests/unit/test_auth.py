"""Unit tests for MSAL authenticators."""

import time
from unittest.mock import patch

import pytest

from powerbi_governance.core.config import Settings
from powerbi_governance.infrastructure.auth import MsalAuthenticator, MsalGraphAuthenticator


def make_settings() -> Settings:
    """Create deterministic settings for authenticator tests."""
    return Settings(
        azure_tenant_id="tenant-id",
        azure_client_id="client-id",
        azure_client_secret="client-secret",
    )


@pytest.mark.unit
class TestMsalAuthenticator:
    """Tests for the Power BI MSAL authenticator."""

    def test_authenticate_uses_confidential_client_credentials(self):
        """Power BI authentication uses client credentials flow with a confidential client."""
        settings = make_settings()
        token_response = {"access_token": "powerbi-token", "expires_in": 3600}

        with patch(
            "powerbi_governance.infrastructure.auth.ConfidentialClientApplication"
        ) as app_cls:
            app = app_cls.return_value
            app.acquire_token_for_client.return_value = token_response

            auth = MsalAuthenticator(settings)
            result = auth.authenticate()

        app_cls.assert_called_once_with(
            client_id="client-id",
            client_credential="client-secret",
            authority="https://login.microsoftonline.com/tenant-id",
        )
        app.acquire_token_for_client.assert_called_once_with(
            scopes=["https://analysis.windows.net/powerbi/api/.default"]
        )
        assert result["access_token"] == "powerbi-token"
        assert result["expires_in"] == 3600
        assert result == token_response
        assert auth._token_cache["_cached_at"] <= time.time()

    def test_get_token_reuses_valid_expires_on_cache(self):
        """Cached tokens with a future expires_on timestamp are reused."""
        auth = MsalAuthenticator(make_settings())
        auth._token_cache = {
            "access_token": "cached-token",
            "expires_on": str(time.time() + 3600),
        }

        with patch.object(auth, "authenticate") as authenticate:
            result = auth.get_token()

        assert result == "cached-token"
        authenticate.assert_not_called()

    def test_get_token_refreshes_expired_expires_in_cache(self):
        """Cached tokens using expires_in are refreshed when their cached time is too old."""
        auth = MsalAuthenticator(make_settings())
        auth._token_cache = {
            "access_token": "expired-token",
            "expires_in": 3600,
            "_cached_at": time.time() - 4000,
        }

        with patch.object(auth, "authenticate") as authenticate:
            authenticate.side_effect = lambda: setattr(
                auth,
                "_token_cache",
                {"access_token": "fresh-token", "expires_in": 3600, "_cached_at": time.time()},
            )
            result = auth.get_token()

        assert result == "fresh-token"
        authenticate.assert_called_once_with()

    def test_invalid_cache_without_expiry_is_refreshed(self):
        """Cached tokens without usable expiry metadata are treated as invalid."""
        auth = MsalAuthenticator(make_settings())
        auth._token_cache = {"access_token": "cached-token"}

        with patch.object(auth, "authenticate") as authenticate:
            authenticate.side_effect = lambda: setattr(
                auth,
                "_token_cache",
                {"access_token": "fresh-token", "expires_in": 3600, "_cached_at": time.time()},
            )
            result = auth.get_token()

        assert result == "fresh-token"
        authenticate.assert_called_once_with()


@pytest.mark.unit
class TestMsalGraphAuthenticator:
    """Tests for the Microsoft Graph MSAL authenticator."""

    def test_authenticate_uses_confidential_client_credentials(self):
        """Graph authentication uses client credentials flow with a confidential client."""
        settings = make_settings()
        token_response = {"access_token": "graph-token", "expires_in": "3600"}

        with patch(
            "powerbi_governance.infrastructure.auth.ConfidentialClientApplication"
        ) as app_cls:
            app = app_cls.return_value
            app.acquire_token_for_client.return_value = token_response

            auth = MsalGraphAuthenticator(settings)
            result = auth.authenticate()

        app_cls.assert_called_once_with(
            client_id="client-id",
            client_credential="client-secret",
            authority="https://login.microsoftonline.com/tenant-id",
        )
        app.acquire_token_for_client.assert_called_once_with(
            scopes=["https://graph.microsoft.com/.default"]
        )
        assert result["access_token"] == "graph-token"
        assert result["expires_in"] == "3600"
        assert result == token_response
        assert auth._token_cache["_cached_at"] <= time.time()

    def test_get_token_reuses_valid_expires_in_cache(self):
        """Cached Graph tokens with expires_in and cached_at are reused before expiry."""
        auth = MsalGraphAuthenticator(make_settings())
        auth._token_cache = {
            "access_token": "cached-token",
            "expires_in": "3600",
            "_cached_at": time.time(),
        }

        with patch.object(auth, "authenticate") as authenticate:
            result = auth.get_token()

        assert result == "cached-token"
        authenticate.assert_not_called()
