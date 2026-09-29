"""
Power BI REST API client
"""

from typing import Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from powerbi_governance.core import Settings, get_settings

log = structlog.get_logger(__name__)


class PowerBIClient:
    """
    Power BI REST API client.
    
    Provides methods for interacting with Power BI Admin APIs and user APIs.
    Handles authentication, retries, and error handling.
    """

    def __init__(self, settings: Optional[Settings] = None, bearer_token: Optional[str] = None) -> None:
        """
        Initialize Power BI client.
        
        Args:
            settings: Application settings
            bearer_token: Bearer token for authentication
        """
        self.settings = settings or get_settings()
        self.bearer_token = bearer_token
        self.base_url = self.settings.powerbi_api_base_url
        self.timeout = self.settings.powerbi_timeout_seconds

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
    async def get_workspaces(self, skip: int = 0, top: int = 100) -> dict:
        """
        Get all workspaces.
        
        Args:
            skip: Number of workspaces to skip (pagination)
            top: Number of workspaces to return
            
        Returns:
            API response with workspaces
        """
        log.info("Fetching workspaces", skip=skip, top=top)

        url = f"{self.base_url}/groups"
        params = {"$skip": skip, "$top": top}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response.json()

    async def get_all_workspaces(self, page_size: int = 100) -> list[dict]:
        """Fetch every workspace exposed by the Power BI groups endpoint.

        ``get_workspaces`` deliberately remains a single-page operation for
        interactive callers. Synchronization flows should use this method so
        their result is not silently limited to the first page.
        """
        if page_size < 1:
            raise ValueError("page_size must be at least 1")

        workspaces: list[dict] = []
        skip = 0
        while True:
            payload = await self.get_workspaces(skip=skip, top=page_size)
            page = payload.get("value", []) if isinstance(payload, dict) else []
            if not isinstance(page, list):
                raise ValueError("Power BI workspaces response has an invalid 'value' field")

            workspaces.extend(item for item in page if isinstance(item, dict))
            if len(page) < page_size:
                break
            skip += len(page)

        log.info("Fetched all workspaces", workspace_count=len(workspaces))
        return workspaces

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_workspace_datasets(self, workspace_id: str) -> dict:
        """
        Get datasets in a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            API response with datasets
        """
        log.info("Fetching datasets", workspace_id=workspace_id)

        url = f"{self.base_url}/groups/{workspace_id}/datasets"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_workspace_reports(self, workspace_id: str) -> dict:
        """
        Get reports in a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            API response with reports
        """
        log.info("Fetching reports", workspace_id=workspace_id)

        url = f"{self.base_url}/groups/{workspace_id}/reports"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_dataset_refresh_history(self, workspace_id: str, dataset_id: str) -> dict:
        """
        Get refresh history for a dataset.
        
        Args:
            workspace_id: Workspace ID
            dataset_id: Dataset ID
            
        Returns:
            API response with refresh history
        """
        log.info("Fetching refresh history", workspace_id=workspace_id, dataset_id=dataset_id)

        url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_activity_events(
        self,
        start_date_time: Optional[str] = None,
        end_date_time: Optional[str] = None,
        continuation_uri: Optional[str] = None,
        filter_expression: Optional[str] = None,
    ) -> dict:
        """
        Get activity events (Admin API required).

        Per the Power BI REST API contract, provide either `continuation_uri` (to
        fetch the next page of a previous request) or both `start_date_time` and
        `end_date_time`, which must fall on the same UTC calendar day and within
        the last 28 days. There is no `$filter` support for dates - only for
        `Activity`/`UserId` equality.

        Args:
            start_date_time: ISO 8601 UTC start of the window, e.g. "2026-09-01T00:00:00.000Z"
            end_date_time: ISO 8601 UTC end of the window, same UTC day as start_date_time
            continuation_uri: Full URL from a previous response's `continuationUri`,
                used to fetch the next page of the same day's results
            filter_expression: Optional OData filter, e.g. "Activity eq 'ViewReport'"

        Returns:
            API response with activity events
        """
        log.info(
            "Fetching activity events",
            start=start_date_time,
            end=end_date_time,
            paginated=bool(continuation_uri),
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if continuation_uri:
                response = await client.get(continuation_uri, headers=self._get_headers())
            else:
                url = f"{self.base_url}/admin/activityevents"
                params = {
                    "startDateTime": f"'{start_date_time}'",
                    "endDateTime": f"'{end_date_time}'",
                }
                if filter_expression:
                    params["$filter"] = filter_expression
                response = await client.get(url, headers=self._get_headers(), params=params)

            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_workspace_users(self, workspace_id: str) -> dict:
        """
        Get users in a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            API response with workspace users
        """
        log.info("Fetching workspace users", workspace_id=workspace_id)

        url = f"{self.base_url}/groups/{workspace_id}/users"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()


__all__ = ["PowerBIClient"]
