"""
Authentication module - Microsoft Authentication Library (MSAL) integration
"""

import time
from typing import Any

import structlog
from msal import ConfidentialClientApplication

from powerbi_governance.core import Settings, get_settings

log = structlog.get_logger(__name__)

_TOKEN_REFRESH_BUFFER_SECONDS = 300
_TOKEN_CACHED_AT_KEY = "_cached_at"
_POWERBI_SCOPES = ["https://analysis.windows.net/powerbi/api/.default"]
_GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]


class MsalAuthenticator:
    """
    MSAL-based authenticator for Service Principal authentication.

    Handles token acquisition and caching for service principal flows.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize authenticator.

        Args:
            settings: Application settings (uses get_settings() if None)
        """
        self.settings = settings or get_settings()
        self.app: ConfidentialClientApplication | None = None
        self._token_cache: dict[str, Any] | None = None

    def authenticate(self) -> dict[str, Any]:
        """
        Authenticate using Service Principal credentials.

        Uses client credentials flow to acquire bearer token for Power BI APIs.

        Returns:
            Token response dictionary with access_token

        Raises:
            Exception: If authentication fails

        Example:
            >>> auth = MsalAuthenticator()
            >>> token = auth.authenticate()
            >>> headers = {"Authorization": f"Bearer {token['access_token']}"}
        """
        try:
            log.info(
                "Authenticating service principal",
                tenant_id=self.settings.azure_tenant_id,
                client_id=self.settings.azure_client_id,
            )

            app = self._get_app()
            token_response = app.acquire_token_for_client(scopes=_POWERBI_SCOPES)

            if "access_token" in token_response:
                self._cache_token(token_response)
                log.info("Authentication successful", expires_in=token_response.get("expires_in"))
                return token_response

            error_msg = token_response.get("error_description", "Unknown error")
            log.error("Authentication failed", error=error_msg)
            raise Exception(f"Authentication failed: {error_msg}")

        except Exception as e:
            log.error("Authentication error", error=str(e))
            raise

    def get_token(self) -> str:
        """
        Get current access token.

        Returns cached token if valid, otherwise authenticates again.

        Returns:
            Bearer token string
        """
        if not self._token_cache or not self._is_token_valid():
            self.authenticate()

        return self._token_cache["access_token"]

    def _get_app(self) -> ConfidentialClientApplication:
        """Create or return the configured confidential client application."""
        if self.app is None:
            self.app = ConfidentialClientApplication(
                client_id=self.settings.azure_client_id,
                client_credential=self.settings.azure_client_secret,
                authority=f"https://login.microsoftonline.com/{self.settings.azure_tenant_id}",
            )
        return self.app

    def _cache_token(self, token_response: dict[str, Any]) -> None:
        """Cache token metadata with enough timing data to validate later."""
        cached_token = dict(token_response)
        cached_token[_TOKEN_CACHED_AT_KEY] = time.time()
        self._token_cache = cached_token

    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid."""
        return _is_token_valid(self._token_cache)


class MsalGraphAuthenticator:
    """
    MSAL authenticator for Microsoft Graph API.

    Handles token acquisition for Graph API endpoints.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize authenticator"""
        self.settings = settings or get_settings()
        self.app: ConfidentialClientApplication | None = None
        self._token_cache: dict[str, Any] | None = None

    def authenticate(self) -> dict[str, Any]:
        """
        Authenticate for Microsoft Graph API.

        Returns:
            Token response with access_token
        """
        try:
            app = self._get_app()
            token_response = app.acquire_token_for_client(scopes=_GRAPH_SCOPES)

            if "access_token" in token_response:
                self._cache_token(token_response)
                return token_response

            raise Exception(token_response.get("error_description", "Authentication failed"))

        except Exception as e:
            log.error("Graph authentication error", error=str(e))
            raise

    def get_token(self) -> str:
        """Get current Graph API access token"""
        if not self._token_cache or not self._is_token_valid():
            self.authenticate()

        return self._token_cache["access_token"]

    def _get_app(self) -> ConfidentialClientApplication:
        """Create or return the configured confidential client application."""
        if self.app is None:
            self.app = ConfidentialClientApplication(
                client_id=self.settings.azure_client_id,
                client_credential=self.settings.azure_client_secret,
                authority=f"https://login.microsoftonline.com/{self.settings.azure_tenant_id}",
            )
        return self.app

    def _cache_token(self, token_response: dict[str, Any]) -> None:
        """Cache token metadata with enough timing data to validate later."""
        cached_token = dict(token_response)
        cached_token[_TOKEN_CACHED_AT_KEY] = time.time()
        self._token_cache = cached_token

    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid."""
        return _is_token_valid(self._token_cache)


def _is_token_valid(token_cache: dict[str, Any] | None) -> bool:
    """Validate cached MSAL token metadata using expires_on or expires_in."""
    if not token_cache or not token_cache.get("access_token"):
        return False

    expires_at = _get_token_expires_at(token_cache)
    if expires_at is None:
        return False

    return expires_at - time.time() > _TOKEN_REFRESH_BUFFER_SECONDS


def _get_token_expires_at(token_cache: dict[str, Any]) -> float | None:
    """Return the token expiry epoch from MSAL expires_on/expires_in metadata."""
    expires_on = _coerce_float(token_cache.get("expires_on"))
    if expires_on is not None:
        return expires_on

    expires_in = _coerce_float(token_cache.get("expires_in"))
    cached_at = _coerce_float(token_cache.get(_TOKEN_CACHED_AT_KEY))
    if expires_in is None or cached_at is None:
        return None

    return cached_at + expires_in


def _coerce_float(value: Any) -> float | None:
    """Safely coerce token timing values to float."""
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "MsalAuthenticator",
    "MsalGraphAuthenticator",
]
