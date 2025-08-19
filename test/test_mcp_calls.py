import pytest

from fastmcp import Client
from unittest.mock import MagicMock
from unittest.mock import ANY

from src.main import mcp_server


@pytest.mark.asyncio
async def test_add_endpoint(mocker):
    create_patch = mocker.patch(
        "src.main.crud.create_or_update_service", return_value=MagicMock(id=1)
    )
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "add_endpoint",
            arguments={
                "endpoint": "http://localhost:8000",
                "description": "Test MCP service",
            },
        )
    assert result.content[0].text == "Create service with id='1'"

    create_patch.assert_called_once_with(
        ANY,
        endpoint="http://localhost:8000",
        description="Test MCP service",
        context=ANY,
    )


@pytest.mark.asyncio
async def test_list_services(mocker):
    patch = mocker.patch(
        "src.main.crud.list_services_brief",
        return_value=[
            {"endpoint": "http://localhost:8000", "description": "Test MCP service"}
        ],
    )
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "list_services",
            arguments={},
        )
    assert (
        result.content[0].text
        == '[{"endpoint":"http://localhost:8000","description":"Test MCP service"}]'
    )

    patch.assert_called_once_with(ANY)


@pytest.mark.asyncio
async def test_remove_service(mocker):
    patch = mocker.patch("src.main.crud.delete_service")
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "remove_service",
            arguments={
                "service_id": "service_123",
            },
        )
    assert result.content[0].text == "Service with id='service_123' removed"
    patch.assert_called_once_with(ANY, "service_123")
