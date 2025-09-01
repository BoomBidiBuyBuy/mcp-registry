import pytest

from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.main import mcp_server


client = TestClient(mcp_server.http_app())


@pytest.mark.asyncio
async def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "mcp-server"}


@pytest.mark.asyncio
async def test_register_user(mocker):
    mocker.patch(
        "src.main.crud.get_or_create_user", return_value=MagicMock(user_id="test_user")
    )
    response = client.post("/register_user", json={"user_id": "test_user"})
    assert response.status_code == 200
    assert response.json() == {"status": "user registered"}


@pytest.mark.asyncio
async def test_list_services(mocker):
    mocker.patch(
        "src.main.crud.list_services_brief",
        return_value=[
            {
                "service_name": "test_service",
                "endpoint": "http://localhost:8000",
                "description": "Test MCP service",
            }
        ],
    )
    response = client.get("/list_services")
    assert response.status_code == 200
    assert response.json() == {
        "services": {
            "test_service": {
                "transport": "streamable_http",
                "url": "http://localhost:8000",
            }
        }
    }
