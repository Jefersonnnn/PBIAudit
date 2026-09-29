"""Tests for Power BI REST client pagination."""

from unittest.mock import AsyncMock

import pytest

from powerbi_governance.infrastructure.clients.powerbi import PowerBIClient


@pytest.mark.unit
async def test_get_all_workspaces_requests_every_page():
    client = object.__new__(PowerBIClient)
    client.get_workspaces = AsyncMock(side_effect=[
        {"value": [{"id": "workspace-1"}, {"id": "workspace-2"}]},
        {"value": [{"id": "workspace-3"}]},
    ])

    workspaces = await client.get_all_workspaces(page_size=2)

    assert [workspace["id"] for workspace in workspaces] == ["workspace-1", "workspace-2", "workspace-3"]
    assert client.get_workspaces.await_args_list[0].kwargs == {"skip": 0, "top": 2}
    assert client.get_workspaces.await_args_list[1].kwargs == {"skip": 2, "top": 2}


@pytest.mark.unit
async def test_get_all_workspaces_rejects_invalid_page_size():
    client = object.__new__(PowerBIClient)

    with pytest.raises(ValueError, match="page_size must be at least 1"):
        await client.get_all_workspaces(page_size=0)


@pytest.mark.unit
async def test_get_all_workspaces_rejects_invalid_response_shape():
    client = object.__new__(PowerBIClient)
    client.get_workspaces = AsyncMock(return_value={"value": {"id": "workspace-1"}})

    with pytest.raises(ValueError, match="invalid 'value' field"):
        await client.get_all_workspaces()
