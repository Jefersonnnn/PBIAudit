"""
Domain services - High-level business operations
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from inspect import isawaitable
from typing import Any, Optional

import structlog

from powerbi_governance.domain.entities import ActivityEvent, LicenseAssignment, UsageMetric, User, Workspace

log = structlog.get_logger(__name__)


async def _maybe_await(value: Any) -> Any:
    """Return awaited values for async repositories/clients, or the value itself."""
    if isawaitable(value):
        return await value
    return value


def _parse_datetime(value: Any) -> datetime:
    """Parse API date values into timezone-aware UTC datetimes."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        parsed = datetime.fromisoformat(normalized)
    else:
        raise ValueError(f"Unsupported datetime value: {value!r}")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _items_from_response(response: Any, *keys: str) -> list[Any]:
    """Extract list-like payloads from the common Power BI/Graph response shapes."""
    if response is None:
        return []
    if isinstance(response, list):
        return response
    if not isinstance(response, Mapping):
        return []

    for key in (*keys, "value", "rows", "events", "activityEventEntities", "activityEvents"):
        value = response.get(key)
        if isinstance(value, list):
            return value
    return []


def _format_activity_event_datetime(value: datetime) -> str:
    """Format a UTC datetime for the Power BI activityevents startDateTime/endDateTime params."""
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


def _first_present(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first non-empty value for any of the provided API field aliases."""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


async def _persist_entity(repository: Any, entity: Any, natural_id: str, lookup_method: str | None = None) -> Any:
    """Persist an entity using an upsert method when available, otherwise create/update."""
    if hasattr(repository, "upsert"):
        return await _maybe_await(repository.upsert(entity))

    existing = None
    if lookup_method and hasattr(repository, lookup_method):
        existing = await _maybe_await(getattr(repository, lookup_method)(natural_id))
    elif hasattr(repository, "get_by_id"):
        existing = await _maybe_await(repository.get_by_id(natural_id))

    if existing is not None and hasattr(repository, "update"):
        return await _maybe_await(repository.update(natural_id, entity))
    if hasattr(repository, "create"):
        return await _maybe_await(repository.create(entity))

    raise AttributeError("Repository must expose upsert or create/update methods")


class WorkspaceService:
    """
    Business logic for workspace operations.

    Orchestrates workspace discovery, synchronization and management.
    """

    def __init__(self, powerbi_client, repository) -> None:
        """
        Initialize workspace service.

        Args:
            powerbi_client: Power BI API client
            repository: Workspace repository for persistence
        """
        self.powerbi_client = powerbi_client
        self.repository = repository

    async def sync_workspaces(self) -> int:
        """
        Discover, normalize and synchronize workspaces from Power BI.

        Returns:
            Number of workspaces synchronized
        """
        log.info("Starting workspace synchronization")

        try:
            workspaces_data = await self.powerbi_client.get_workspaces()
            workspace_items = _items_from_response(workspaces_data, "workspaces")

            workspace_count = 0
            for item in workspace_items:
                if not isinstance(item, Mapping):
                    log.warning("Skipping invalid workspace payload", payload_type=type(item).__name__)
                    continue

                workspace_id = _first_present(item, "id", "workspaceId", "groupId")
                if not workspace_id:
                    log.warning("Skipping workspace without identifier", workspace=item)
                    continue

                workspace = Workspace(
                    workspace_id=str(workspace_id),
                    name=str(_first_present(item, "name", "displayName", default="Unnamed workspace")),
                    description=_first_present(item, "description"),
                    is_premium=bool(
                        _first_present(item, "isOnDedicatedCapacity", "is_on_dedicated_capacity", default=False)
                        or _first_present(item, "capacityId", "capacity_id")
                    ),
                    state=str(_first_present(item, "state", default="ACTIVE")),
                    is_on_dedicated_capacity=bool(
                        _first_present(item, "isOnDedicatedCapacity", "is_on_dedicated_capacity", default=False)
                    ),
                    capacity_id=_first_present(item, "capacityId", "capacity_id"),
                )

                await _persist_entity(self.repository, workspace, workspace.workspace_id, "get_by_workspace_id")
                workspace_count += 1

            log.info(
                "Workspace synchronization completed",
                fetched_count=len(workspace_items),
                synchronized_count=workspace_count,
            )
            return workspace_count

        except Exception as e:
            log.exception("Workspace synchronization failed", error=str(e))
            raise RuntimeError(f"Workspace synchronization failed: {e}") from e

    async def get_workspace_datasets(self, workspace_id: str) -> list:
        """
        Get datasets in a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of datasets
        """
        log.info("Fetching datasets for workspace", workspace_id=workspace_id)

        try:
            datasets_data = await self.powerbi_client.get_workspace_datasets(workspace_id)
            return datasets_data.get("value", [])

        except Exception as e:
            log.exception("Failed to fetch datasets", workspace_id=workspace_id, error=str(e))
            raise RuntimeError(f"Failed to fetch datasets for workspace {workspace_id}: {e}") from e


class UsageMetricsService:
    """
    Business logic for usage metrics collection.

    Handles collection, aggregation and storage of usage metrics.
    """

    def __init__(self, powerbi_client, xmla_client, repository) -> None:
        """
        Initialize usage metrics service.

        Args:
            powerbi_client: Power BI API client
            xmla_client: XMLA client for DAX queries
            repository: Repository for persistence
        """
        self.powerbi_client = powerbi_client
        self.xmla_client = xmla_client
        self.repository = repository

    async def sync_usage_metrics(self) -> int:
        """
        Synchronize usage metrics from Power BI.

        Returns:
            Number of metrics synchronized
        """
        log.info("Starting usage metrics synchronization")

        try:
            workspaces = _items_from_response(await self.powerbi_client.get_workspaces(), "workspaces")
            metrics_count = 0
            report_count = 0
            dataset_count = 0

            for workspace in workspaces:
                workspace_id = str(_first_present(workspace, "id", "workspaceId", "groupId", default=""))
                if not workspace_id:
                    log.warning("Skipping usage metric workspace without identifier", workspace=workspace)
                    continue

                datasets = _items_from_response(
                    await self.powerbi_client.get_workspace_datasets(workspace_id), "datasets"
                )
                reports = _items_from_response(await self.powerbi_client.get_workspace_reports(workspace_id), "reports")
                dataset_count += len(datasets)
                report_count += len(reports)
                reports_by_dataset: dict[str, list[Mapping[str, Any]]] = {}

                for report in reports:
                    if isinstance(report, Mapping):
                        dataset_id = _first_present(report, "datasetId", "dataset_id")
                        if dataset_id:
                            reports_by_dataset.setdefault(str(dataset_id), []).append(report)

                for dataset in datasets:
                    if not isinstance(dataset, Mapping):
                        log.warning("Skipping invalid dataset payload", workspace_id=workspace_id)
                        continue

                    dataset_id = str(_first_present(dataset, "id", "datasetId", default=""))
                    if not dataset_id:
                        log.warning("Skipping dataset without identifier", workspace_id=workspace_id, dataset=dataset)
                        continue

                    metrics_payload = await self.xmla_client.get_usage_metrics_table(dataset_id)
                    metric_rows = _items_from_response(metrics_payload, "metrics", "usageMetrics")
                    for metric in self._normalize_usage_metrics(
                        metric_rows,
                        workspace_id=workspace_id,
                        dataset_id=dataset_id,
                        reports=reports_by_dataset.get(dataset_id, []),
                    ):
                        await _persist_entity(self.repository, metric, metric.report_id)
                        metrics_count += 1

            log.info(
                "Usage metrics synchronization completed",
                workspace_count=len(workspaces),
                dataset_count=dataset_count,
                report_count=report_count,
                synchronized_count=metrics_count,
            )
            return metrics_count

        except Exception as e:
            log.exception("Usage metrics synchronization failed", error=str(e))
            raise RuntimeError(f"Usage metrics synchronization failed: {e}") from e

    def _normalize_usage_metrics(
        self,
        rows: Iterable[Any],
        *,
        workspace_id: str,
        dataset_id: str,
        reports: list[Mapping[str, Any]],
    ) -> list[UsageMetric]:
        """Normalize XMLA usage metric rows into domain entities."""
        metrics: list[UsageMetric] = []
        default_report = reports[0] if reports else {}

        for row in rows:
            if not isinstance(row, Mapping):
                log.warning("Skipping invalid usage metric payload", dataset_id=dataset_id)
                continue

            report_id = str(
                _first_present(row, "report_id", "reportId", "ReportId", default="")
                or _first_present(default_report, "id", "reportId", default=dataset_id)
            )
            metric_date_value = _first_present(row, "metric_date", "metricDate", "Date", "date")
            if metric_date_value is None:
                log.warning("Skipping usage metric without metric date", dataset_id=dataset_id, report_id=report_id)
                continue

            metrics.append(
                UsageMetric(
                    report_id=report_id,
                    workspace_id=str(_first_present(row, "workspace_id", "workspaceId", default=workspace_id)),
                    metric_date=_parse_datetime(metric_date_value),
                    views=int(_first_present(row, "views", "Views", "viewCount", default=0) or 0),
                    unique_viewers=int(
                        _first_present(row, "unique_viewers", "uniqueViewers", "UniqueViewers", default=0) or 0
                    ),
                )
            )
        return metrics


class ActivityEventsService:
    """
    Business logic for activity events collection.

    Handles audit log collection and storage.
    """

    def __init__(self, powerbi_client, repository) -> None:
        """
        Initialize activity events service.

        Args:
            powerbi_client: Power BI API client
            repository: Repository for persistence
        """
        self.powerbi_client = powerbi_client
        self.repository = repository

    async def sync_activity_events(self, days_back: int = 1) -> int:
        """
        Synchronize activity events from audit logs.

        Queries one full UTC calendar day at a time (rather than a rolling 24h
        window), since the Power BI Admin API requires startDateTime/endDateTime
        to fall on the same UTC day and only retains 28 days of history.

        Args:
            days_back: Number of days to collect events for (max 28)

        Returns:
            Number of events synchronized
        """
        log.info("Starting activity events synchronization", days=days_back)

        try:
            if days_back < 1:
                raise ValueError("days_back must be at least 1")
            if days_back > 28:
                raise ValueError(
                    "days_back cannot exceed 28 - the Power BI Admin API only retains "
                    "28 days of activity events"
                )

            events_count = 0
            today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

            for day_offset in range(days_back):
                day_start = today - timedelta(days=day_offset)
                day_end = day_start + timedelta(days=1, milliseconds=-1)

                window_count = 0
                continuation_uri: Optional[str] = None
                while True:
                    if continuation_uri:
                        events_payload = await self.powerbi_client.get_activity_events(
                            continuation_uri=continuation_uri
                        )
                    else:
                        events_payload = await self.powerbi_client.get_activity_events(
                            start_date_time=_format_activity_event_datetime(day_start),
                            end_date_time=_format_activity_event_datetime(day_end),
                        )

                    raw_events = _items_from_response(events_payload)
                    for raw_event in raw_events:
                        event = self._normalize_activity_event(raw_event)
                        if event is None:
                            continue
                        await _persist_entity(self.repository, event, event.event_id)
                        events_count += 1
                        window_count += 1

                    continuation_uri = (
                        events_payload.get("continuationUri") if isinstance(events_payload, Mapping) else None
                    )
                    if not continuation_uri:
                        break

                log.info(
                    "Activity events window synchronized",
                    window_start=day_start.isoformat(),
                    window_end=day_end.isoformat(),
                    synchronized_count=window_count,
                )

            log.info("Activity events synchronization completed", synchronized_count=events_count, days=days_back)
            return events_count

        except Exception as e:
            log.exception("Activity events synchronization failed", days=days_back, error=str(e))
            raise RuntimeError(f"Activity events synchronization failed for {days_back} day(s): {e}") from e

    def _normalize_activity_event(self, raw_event: Any) -> ActivityEvent | None:
        """Normalize Power BI audit activity events into domain entities."""
        if not isinstance(raw_event, Mapping):
            log.warning("Skipping invalid activity event payload", payload_type=type(raw_event).__name__)
            return None

        event_id = _first_present(raw_event, "Id", "id", "eventId", "RecordId")
        event_time = _first_present(raw_event, "CreationTime", "ActivityDateTime", "eventTime", "TimeGenerated")
        user_id = _first_present(raw_event, "UserId", "userId", "UserKey", "ActorUserPrincipalName")
        activity = _first_present(raw_event, "Activity", "activity", "Operation", default="Unknown")

        if not event_id or not event_time or not user_id:
            log.warning("Skipping activity event missing required fields", event=raw_event)
            return None

        resource_id = _first_present(
            raw_event, "ArtifactId", "ObjectId", "DatasetId", "ReportId", "WorkspaceId", "resourceId"
        )
        resource_type = _first_present(raw_event, "ArtifactKind", "Workload", "ItemType", "resourceType")
        resource_name = _first_present(raw_event, "ArtifactName", "ObjectName", "ItemName", "resourceName")

        return ActivityEvent(
            event_id=str(event_id),
            user_id=str(user_id).lower(),
            activity=str(activity),
            resource_id=str(resource_id) if resource_id is not None else None,
            resource_type=str(resource_type) if resource_type is not None else None,
            resource_name=str(resource_name) if resource_name is not None else None,
            event_time=_parse_datetime(event_time),
            details=dict(raw_event),
        )


class UserService:
    """
    Business logic for user management and analysis.

    Handles user synchronization, activity tracking and analysis.
    """

    def __init__(self, graph_client, powerbi_client, repository) -> None:
        """
        Initialize user service.

        Args:
            graph_client: Microsoft Graph client
            powerbi_client: Power BI API client
            repository: Repository for persistence
        """
        self.graph_client = graph_client
        self.powerbi_client = powerbi_client
        self.repository = repository

    async def identify_inactive_users(self, days_inactive: int = 30) -> list:
        """
        Identify users without recent activity.

        Args:
            days_inactive: Number of days without activity

        Returns:
            List of inactive users
        """
        log.info("Identifying inactive users", days=days_inactive)

        try:
            if days_inactive < 1:
                raise ValueError("days_inactive must be at least 1")

            cutoff = datetime.now(UTC) - timedelta(days=days_inactive)
            users = await self._collect_known_users()
            last_activity = await self._collect_last_activity_by_user()

            inactive_users = []
            for user in users.values():
                activity_time = max(
                    (
                        timestamp
                        for user_key in {user.email.lower(), user.user_id.lower()}
                        if (timestamp := last_activity.get(user_key)) is not None
                    ),
                    default=None,
                )
                if activity_time is None or activity_time < cutoff:
                    inactive_users.append(user)

            log.info(
                "Inactive users identification completed",
                user_count=len(users),
                users_with_activity_count=len(last_activity),
                inactive_count=len(inactive_users),
                cutoff=cutoff.isoformat(),
            )
            return inactive_users

        except Exception as e:
            log.exception("Inactive users identification failed", days=days_inactive, error=str(e))
            raise RuntimeError(f"Inactive users identification failed for {days_inactive} day(s): {e}") from e

    async def _collect_known_users(self) -> dict[str, User]:
        """Collect users from Microsoft Graph and Power BI workspace memberships."""
        users: dict[str, User] = {}
        graph_users = _items_from_response(await self.graph_client.get_users(), "users")

        for raw_user in graph_users:
            user = self._normalize_user(raw_user)
            if user is not None:
                users[user.email.lower()] = user

        workspaces = _items_from_response(await self.powerbi_client.get_workspaces(), "workspaces")
        for workspace in workspaces:
            workspace_id = _first_present(workspace, "id", "workspaceId", "groupId")
            if not workspace_id:
                continue
            workspace_users = _items_from_response(
                await self.powerbi_client.get_workspace_users(str(workspace_id)), "users"
            )
            for raw_user in workspace_users:
                user = self._normalize_user(raw_user)
                if user is not None:
                    users.setdefault(user.email.lower(), user)

        return users

    async def _collect_last_activity_by_user(self) -> dict[str, datetime]:
        """Read persisted activity and calculate the latest event timestamp for each user."""
        if hasattr(self.repository, "get_last_activity_by_user"):
            raw_activity = await _maybe_await(self.repository.get_last_activity_by_user())
            return self._normalize_last_activity(raw_activity)

        if hasattr(self.repository, "get_activity_events"):
            raw_activity = await _maybe_await(self.repository.get_activity_events())
        elif hasattr(self.repository, "get_all_activity_events"):
            raw_activity = await _maybe_await(self.repository.get_all_activity_events())
        elif hasattr(self.repository, "get_all"):
            raw_activity = await _maybe_await(self.repository.get_all())
        else:
            raw_activity = []

        return self._normalize_last_activity(raw_activity)

    def _normalize_last_activity(self, raw_activity: Any) -> dict[str, datetime]:
        """Normalize persisted activity rows/mappings into {user_key: latest_datetime}."""
        last_activity: dict[str, datetime] = {}
        activity_items = raw_activity.items() if isinstance(raw_activity, Mapping) else enumerate(raw_activity or [])

        for key, value in activity_items:
            if isinstance(raw_activity, Mapping):
                user_key = str(key).lower()
                event_time = _parse_datetime(value)
            elif isinstance(value, Mapping):
                user_key = str(_first_present(value, "user_id", "userId", "email", "UserId", default="")).lower()
                event_time = _parse_datetime(
                    _first_present(value, "event_time", "eventTime", "last_activity_at", "CreationTime")
                )
            else:
                user_key = str(getattr(value, "user_id", "") or getattr(value, "email", "")).lower()
                event_time = _parse_datetime(
                    getattr(value, "event_time", None) or getattr(value, "last_activity_at", None)
                )

            if not user_key:
                continue
            if user_key not in last_activity or event_time > last_activity[user_key]:
                last_activity[user_key] = event_time

        return last_activity

    def _normalize_user(self, raw_user: Any) -> User | None:
        """Normalize Graph or Power BI user payloads into User entities."""
        if not isinstance(raw_user, Mapping):
            log.warning("Skipping invalid user payload", payload_type=type(raw_user).__name__)
            return None

        email = _first_present(
            raw_user,
            "mail",
            "emailAddress",
            "email",
            "userPrincipalName",
            "identifier",
            "UserPrincipalName",
        )
        user_id = _first_present(raw_user, "id", "user_id", "graphId", "identifier", default=email)
        if not email or not user_id:
            log.warning("Skipping user without identity fields", user=raw_user)
            return None

        return User(
            user_id=str(user_id),
            email=str(email).lower(),
            display_name=str(_first_present(raw_user, "displayName", "display_name", "name", default=email)),
            is_admin=str(_first_present(raw_user, "groupUserAccessRight", "accessRight", default="")).lower() == "admin",
            is_active=bool(_first_present(raw_user, "accountEnabled", "is_active", default=True)),
        )


@dataclass
class LicenseUsageRow:
    """One row of the license-vs-usage audit report."""

    display_name: str
    email: str
    license_type: str
    is_account_enabled: bool
    last_access: Optional[datetime]
    days_since_access: Optional[int]
    resources: list[str] = field(default_factory=list)
    job_title: Optional[str] = None
    department: Optional[str] = None


class LicenseService:
    """
    Business logic for Power BI license auditing.

    Cross-references Power BI-related Microsoft 365 license assignments
    (Microsoft Graph) with persisted Power BI activity events, to identify
    licensed users who are not actually using Power BI.
    """

    # Microsoft's stable service plan identifiers for Power BI licenses.
    # Reference: "Product names and service plan identifiers for licensing".
    _KNOWN_SERVICE_PLANS: dict[str, str] = {
        "BI_AZURE_P0": "Power BI (Free)",
        "BI_AZURE_P1": "Power BI Pro (legacy)",
        "BI_AZURE_P2": "Power BI Pro",
        "BI_AZURE_P3": "Power BI Premium",
        "PBI_PREMIUM_PER_USER": "Power BI Premium Per User",
        "PBI_PREMIUM_PER_USER_ADDON": "Power BI Premium Per User Add-On",
        "PBI_PREMIUM_PER_USER_FACULTY": "Power BI Premium Per User (Faculty)",
    }
    _RELEVANT_SERVICE_PLAN_PREFIXES = ("BI_AZURE_", "PBI_PREMIUM_")

    def __init__(self, graph_client, repository, user_repository=None) -> None:
        """
        Initialize license service.

        Args:
            graph_client: Microsoft Graph client
            repository: License assignment repository for persistence
            user_repository: Optional user repository, used to persist each
                user's job title/department alongside their license so the
                usage report can show who (role-wise) holds an idle license
        """
        self.graph_client = graph_client
        self.repository = repository
        self.user_repository = user_repository

    async def sync_license_assignments(self) -> int:
        """
        Fetch every Power BI-related license assignment from Microsoft Graph
        and replace the persisted snapshot with it. Also upserts each user's
        profile (display name, job title, department) when a user_repository
        was provided.

        Returns:
            Number of license assignments synchronized
        """
        log.info("Starting license assignment synchronization")

        try:
            skus_payload = await self.graph_client.get_subscribed_skus()
            plan_id_to_name = self._build_service_plan_id_map(_items_from_response(skus_payload))

            raw_users = await self.graph_client.get_all_users_with_licenses()
            synced_at = datetime.utcnow()

            assignments: list[LicenseAssignment] = []
            for raw_user in raw_users:
                assignments.extend(self._extract_license_assignments(raw_user, plan_id_to_name, synced_at))

                if self.user_repository is not None:
                    profile = self._build_user_profile(raw_user)
                    if profile is not None:
                        await _maybe_await(self.user_repository.create(profile))

            synced_count = self.repository.replace_all(assignments)
            log.info(
                "License assignment synchronization completed",
                user_count=len(raw_users),
                assignment_count=synced_count,
            )
            return synced_count

        except Exception as e:
            log.exception("License assignment synchronization failed", error=str(e))
            raise RuntimeError(f"License assignment synchronization failed: {e}") from e

    def build_usage_report(self, activity_summary: Mapping[str, Mapping[str, Any]]) -> list[LicenseUsageRow]:
        """
        Combine the current license snapshot with a per-user activity summary.

        Args:
            activity_summary: Mapping produced by
                ``ActivityEventRepository.get_usage_summary_by_user`` —
                lowercased email/UPN to {"last_access": datetime, "resources": set[str]}

        Returns:
            One row per license assignment, sorted with the longest-idle
            (or never-used) licenses first.
        """
        now = datetime.utcnow()
        rows: list[LicenseUsageRow] = []

        for assignment in self.repository.get_all():
            activity = activity_summary.get(assignment.email.lower())
            last_access = activity["last_access"] if activity else None
            resources = sorted(activity["resources"]) if activity else []
            days_since_access = (now - last_access).days if last_access else None

            job_title = department = None
            if self.user_repository is not None:
                user = self.user_repository.get_by_email(assignment.email)
                if user is not None:
                    job_title = user.job_title
                    department = user.department

            rows.append(
                LicenseUsageRow(
                    display_name=assignment.display_name,
                    email=assignment.email,
                    license_type=assignment.license_type,
                    is_account_enabled=assignment.is_account_enabled,
                    last_access=last_access,
                    days_since_access=days_since_access,
                    resources=resources,
                    job_title=job_title,
                    department=department,
                )
            )

        rows.sort(key=lambda row: (row.days_since_access is None, row.days_since_access or 0), reverse=True)
        return rows

    def _build_service_plan_id_map(self, skus: Iterable[Any]) -> dict[str, str]:
        """Map servicePlanId -> raw servicePlanName from the tenant's subscribed SKUs."""
        plan_id_to_name: dict[str, str] = {}
        for sku in skus:
            if not isinstance(sku, Mapping):
                continue
            for plan in sku.get("servicePlans") or []:
                if not isinstance(plan, Mapping):
                    continue
                plan_id = plan.get("servicePlanId")
                plan_name = plan.get("servicePlanName")
                if plan_id and plan_name:
                    plan_id_to_name[str(plan_id)] = str(plan_name)
        return plan_id_to_name

    def _extract_license_assignments(
        self, raw_user: Any, plan_id_to_name: Mapping[str, str], synced_at: datetime
    ) -> list[LicenseAssignment]:
        """Extract Power BI-related license assignments for a single Graph user payload."""
        if not isinstance(raw_user, Mapping):
            log.warning("Skipping invalid user payload", payload_type=type(raw_user).__name__)
            return []

        email = _first_present(raw_user, "mail", "userPrincipalName")
        user_id = _first_present(raw_user, "id", default=email)
        if not email or not user_id:
            log.warning("Skipping user without identity fields", user=raw_user)
            return []

        display_name = str(_first_present(raw_user, "displayName", default=email))
        is_enabled = bool(_first_present(raw_user, "accountEnabled", default=True))

        assignments: list[LicenseAssignment] = []
        seen_plans: set[str] = set()

        for plan in raw_user.get("assignedPlans") or []:
            if not isinstance(plan, Mapping):
                continue
            if str(plan.get("capabilityStatus", "")).lower() != "enabled":
                continue

            raw_name = plan_id_to_name.get(str(plan.get("servicePlanId")))
            if not raw_name or raw_name in seen_plans or not self._is_power_bi_plan(raw_name):
                continue
            seen_plans.add(raw_name)

            assignments.append(
                LicenseAssignment(
                    user_id=str(user_id),
                    email=str(email).lower(),
                    display_name=display_name,
                    license_type=self._KNOWN_SERVICE_PLANS.get(raw_name, raw_name),
                    service_plan_name=raw_name,
                    is_account_enabled=is_enabled,
                    synced_at=synced_at,
                )
            )

        return assignments

    def _build_user_profile(self, raw_user: Any) -> User | None:
        """Build a User entity (display name, job title, department) from a Graph user payload."""
        if not isinstance(raw_user, Mapping):
            return None

        email = _first_present(raw_user, "mail", "userPrincipalName")
        user_id = _first_present(raw_user, "id", default=email)
        if not email or not user_id:
            return None

        return User(
            user_id=str(user_id),
            email=str(email).lower(),
            display_name=str(_first_present(raw_user, "displayName", default=email)),
            job_title=_first_present(raw_user, "jobTitle"),
            department=_first_present(raw_user, "department"),
            is_active=bool(_first_present(raw_user, "accountEnabled", default=True)),
        )

    @classmethod
    def _is_power_bi_plan(cls, raw_service_plan_name: str) -> bool:
        """Check whether a raw Microsoft service plan name is a Power BI license."""
        return raw_service_plan_name in cls._KNOWN_SERVICE_PLANS or raw_service_plan_name.startswith(
            cls._RELEVANT_SERVICE_PLAN_PREFIXES
        )


__all__ = [
    "WorkspaceService",
    "UsageMetricsService",
    "ActivityEventsService",
    "UserService",
    "LicenseService",
    "LicenseUsageRow",
]
