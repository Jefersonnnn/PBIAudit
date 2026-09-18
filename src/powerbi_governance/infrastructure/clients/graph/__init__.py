"""
Microsoft Graph API client

Reference: https://learn.microsoft.com/en-us/graph/overview?context=graph%2Fapi%2F1.0&view=graph-rest-1.0
"""

from typing import Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from powerbi_governance.core import Settings, get_settings

log = structlog.get_logger(__name__)


class GraphClient:
    """
    Microsoft Graph API client.
    
    Provides methods for interacting with Microsoft Graph API,
    including user, group, and organizational information.
    """

    def __init__(self, settings: Optional[Settings] = None, bearer_token: Optional[str] = None) -> None:
        """
        Initialize Graph client.
        
        Args:
            settings: Application settings
            bearer_token: Bearer token for authentication
        """
        self.settings = settings or get_settings()
        self.bearer_token = bearer_token
        self.base_url = self.settings.graph_api_base_url
        self.timeout = self.settings.graph_timeout_seconds

    def _get_headers(self) -> dict:
        """Get request headers with authorization"""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_users(self, filter_expression: Optional[str] = None) -> dict:
        """
        Get users from Azure AD.
        
        Args:
            filter_expression: Optional OData filter expression
            
        Returns:
            API response with users
        """
        log.info("Fetching users from Graph", filter=filter_expression)

        url = f"{self.base_url}/users"
        params = {}

        if filter_expression:
            params["$filter"] = filter_expression

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_user_by_id(self, user_id: str) -> dict:
        """
        Get a specific user.
        
        Args:
            user_id: User ID or UPN
            
        Returns:
            API response with user details
        """
        log.info("Fetching user", user_id=user_id)

        url = f"{self.base_url}/users/{user_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_groups(self) -> dict:
        """
        Get Azure AD groups.
        
        Returns:
            API response with groups
        """
        log.info("Fetching groups from Graph")

        url = f"{self.base_url}/groups"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_subscribed_skus(self) -> dict:
        """
        Get the tenant's subscribed license SKUs and their service plans.

        Used to translate a user's ``assignedPlans[].servicePlanId`` values
        into human-readable service plan names (e.g. "BI_AZURE_P2").

        Requires Organization.Read.All or Directory.Read.All (application permission).

        Returns:
            API response with subscribed SKUs
        """
        log.info("Fetching subscribed SKUs from Graph")

        url = f"{self.base_url}/subscribedSkus"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def get_all_users_with_licenses(self, page_size: int = 999) -> list[dict]:
        """
        Fetch every Azure AD user with the fields needed for license auditing,
        following ``@odata.nextLink`` pagination until exhausted.

        Requires User.Read.All (application permission).

        Args:
            page_size: Page size requested per Graph call (max 999)

        Returns:
            List of raw user payloads with id, displayName, mail,
            userPrincipalName, accountEnabled, assignedPlans, jobTitle
            and department
        """
        log.info("Fetching all users with license info from Graph")

        select_fields = ",".join(
            [
                "id",
                "displayName",
                "mail",
                "userPrincipalName",
                "accountEnabled",
                "assignedPlans",
                "jobTitle",
                "department",
            ]
        )
        url = f"{self.base_url}/users"
        params: Optional[dict] = {"$select": select_fields, "$top": page_size}

        users: list[dict] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while url:
                response = await client.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()
                payload = response.json()

                users.extend(payload.get("value", []))
                url = payload.get("@odata.nextLink")
                params = None  # nextLink already includes query parameters

        log.info("Fetched users with license info", user_count=len(users))
        return users

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_organization(self) -> dict:
        """
        Get organization information.
        
        Returns:
            API response with organization details
        """
        log.info("Fetching organization info")

        url = f"{self.base_url}/organization"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()


__all__ = ["GraphClient"]
