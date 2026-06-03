"""
Authentication module - Microsoft Authentication Library (MSAL) integration
"""

from typing import Optional

import structlog
from msal import PublicClientApplication

from powerbi_governance.core import Settings, get_settings, security

log = structlog.get_logger(__name__)


class MsalAuthenticator:
    """
    MSAL-based authenticator for Service Principal authentication.
    
    Handles token acquisition and caching for service principal flows.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Initialize authenticator.
        
        Args:
            settings: Application settings (uses get_settings() if None)
        """
        self.settings = settings or get_settings()
        self.app: Optional[PublicClientApplication] = None
        self._token_cache: Optional[dict] = None

    def authenticate(self) -> dict:
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

            # Create MSAL application
            app = PublicClientApplication(
                client_id=self.settings.azure_client_id,
                authority=f"https://login.microsoftonline.com/{self.settings.azure_tenant_id}",
            )

            # Acquire token using client credentials
            # Note: For service principal, use client credentials flow
            token_response = app.acquire_token_for_client(
                scopes=["https://analysis.windows.net/powerbi/api/.default"]
            )

            if "access_token" in token_response:
                self._token_cache = token_response
                log.info("Authentication successful", expires_in=token_response.get("expires_in"))
                return token_response
            else:
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

    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid"""
        if not self._token_cache:
            return False

        import time

        expires_at = self._token_cache.get("expires_on", 0)
        current_time = time.time()

        # Refresh if less than 5 minutes remaining
        return expires_at - current_time > 300


class MsalGraphAuthenticator:
    """
    MSAL authenticator for Microsoft Graph API.
    
    Handles token acquisition for Graph API endpoints.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize authenticator"""
        self.settings = settings or get_settings()
        self._token_cache: Optional[dict] = None

    def authenticate(self) -> dict:
        """
        Authenticate for Microsoft Graph API.
        
        Returns:
            Token response with access_token
        """
        try:
            app = PublicClientApplication(
                client_id=self.settings.azure_client_id,
                authority=f"https://login.microsoftonline.com/{self.settings.azure_tenant_id}",
            )

            token_response = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )

            if "access_token" in token_response:
                self._token_cache = token_response
                return token_response
            else:
                raise Exception(token_response.get("error_description", "Authentication failed"))

        except Exception as e:
            log.error("Graph authentication error", error=str(e))
            raise

    def get_token(self) -> str:
        """Get current Graph API access token"""
        if not self._token_cache or not self._is_token_valid():
            self.authenticate()

        return self._token_cache["access_token"]

    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid"""
        if not self._token_cache:
            return False

        import time

        expires_at = self._token_cache.get("expires_on", 0)
        current_time = time.time()

        return expires_at - current_time > 300


__all__ = [
    "MsalAuthenticator",
    "MsalGraphAuthenticator",
]
