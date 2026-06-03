"""
CLI - Command Line Interface Usage Examples

Demonstrates how to use the PowerBI Governance CLI.
"""

import asyncio

from powerbi_governance.core import get_settings, configure_logging
from powerbi_governance.infrastructure.auth import MsalAuthenticator
from powerbi_governance.infrastructure.clients.powerbi import PowerBIClient
from powerbi_governance.infrastructure.clients.graph import GraphClient


async def example_sync_workspaces():
    """Example: Sync workspaces from Power BI"""
    settings = get_settings()
    configure_logging(settings)

    # Authenticate
    auth = MsalAuthenticator(settings)
    token_response = auth.authenticate()
    token = token_response["access_token"]

    # Create client
    client = PowerBIClient(settings, token)

    # Fetch workspaces
    workspaces = await client.get_workspaces(skip=0, top=100)

    print(f"Found {len(workspaces['value'])} workspaces:")
    for ws in workspaces["value"]:
        print(f"  - {ws.get('displayName', 'Unknown')} (Premium: {ws.get('isOnDedicatedCapacity', False)})")


async def example_fetch_datasets():
    """Example: Fetch datasets from a workspace"""
    settings = get_settings()
    configure_logging(settings)

    auth = MsalAuthenticator(settings)
    token_response = auth.authenticate()
    token = token_response["access_token"]

    client = PowerBIClient(settings, token)

    # Get first workspace (example)
    workspace_id = "your-workspace-id"
    datasets = await client.get_workspace_datasets(workspace_id)

    print(f"Found {len(datasets['value'])} datasets:")
    for ds in datasets["value"]:
        print(f"  - {ds.get('name', 'Unknown')} (Refreshes: {ds.get('configuredRefreshes', [])[:3]}...)")


async def example_graph_api():
    """Example: Query Microsoft Graph"""
    settings = get_settings()
    configure_logging(settings)

    from powerbi_governance.infrastructure.auth import MsalGraphAuthenticator

    auth = MsalGraphAuthenticator(settings)
    token_response = auth.authenticate()
    token = token_response["access_token"]

    client = GraphClient(settings, token)

    # Get users
    users = await client.get_users()

    print(f"Found {len(users['value'])} users in Azure AD:")
    for user in users["value"][:5]:  # Show first 5
        print(f"  - {user.get('mail')} ({user.get('displayName')})")


async def example_full_sync_pipeline():
    """Example: Complete sync pipeline"""
    settings = get_settings()
    configure_logging(settings)

    # Setup
    auth = MsalAuthenticator(settings)
    token_response = auth.authenticate()
    token = token_response["access_token"]

    powerbi_client = PowerBIClient(settings, token)

    # Step 1: Sync workspaces
    print("Step 1: Syncing workspaces...")
    workspaces = await powerbi_client.get_workspaces(top=50)
    workspace_count = len(workspaces["value"])
    print(f"  ✓ Synced {workspace_count} workspaces")

    # Step 2: For each workspace, sync datasets
    print("Step 2: Syncing datasets...")
    total_datasets = 0
    for workspace in workspaces["value"]:
        ws_id = workspace["id"]
        datasets = await powerbi_client.get_workspace_datasets(ws_id)
        total_datasets += len(datasets["value"])

    print(f"  ✓ Synced {total_datasets} datasets")

    # Step 3: For each workspace, sync reports
    print("Step 3: Syncing reports...")
    total_reports = 0
    for workspace in workspaces["value"]:
        ws_id = workspace["id"]
        reports = await powerbi_client.get_workspace_reports(ws_id)
        total_reports += len(reports["value"])

    print(f"  ✓ Synced {total_reports} reports")

    # Summary
    print("\n📊 Sync Summary:")
    print(f"  Workspaces: {workspace_count}")
    print(f"  Datasets: {total_datasets}")
    print(f"  Reports: {total_reports}")


if __name__ == "__main__":
    print("PowerBI Governance - CLI Usage Examples\n")

    print("Example 1: Sync Workspaces")
    print("=" * 50)
    # asyncio.run(example_sync_workspaces())

    print("\n\nExample 2: Fetch Datasets")
    print("=" * 50)
    # asyncio.run(example_fetch_datasets())

    print("\n\nExample 3: Graph API")
    print("=" * 50)
    # asyncio.run(example_graph_api())

    print("\n\nExample 4: Full Sync Pipeline")
    print("=" * 50)
    # asyncio.run(example_full_sync_pipeline())

    print("\nNote: Uncomment examples to run (requires valid Azure credentials)")
