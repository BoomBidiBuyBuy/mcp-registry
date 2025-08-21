import pytest

from fastmcp import Client
from unittest.mock import MagicMock
from unittest.mock import ANY

from src.main import mcp_server


@pytest.mark.asyncio
async def test_add_service(mocker):
    create_patch = mocker.patch(
        "src.main.crud.create_or_update_service",
        return_value=MagicMock(service_name="svc1", tools=[]),
    )
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "add_service",
            arguments={
                "service_name": "svc1",
                "endpoint": "http://localhost:8000",
                "description": "Test MCP service",
                "requires_authorization": True,
                "method_authorization": "Basic",
            },
        )
    assert result.content[0].text == "Create service with name='svc1'"

    create_patch.assert_called_once_with(
        ANY,
        service_name="svc1",
        endpoint="http://localhost:8000",
        description="Test MCP service",
        requires_authorization=True,
        method_authorization="Basic",
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
                "service_name": "svc1",
            },
        )
    assert result.content[0].text == "Service with name='svc1' removed"
    patch.assert_called_once_with(ANY, "svc1")
