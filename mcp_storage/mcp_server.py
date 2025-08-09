from __future__ import annotations

from typing import Any
import os
import logging

from fastmcp import FastMCP

from .storage import get_engine_and_sessionmaker, init_db
from . import crud


mcp = FastMCP(
    name="mcp-storage",
    description="A MCP registry that stores other MCP service endpoints, descriptions, and their available tools.",
)

engine, SessionLocal = get_engine_and_sessionmaker()
init_db(engine)

# Configure logging
logger = logging.getLogger("mcp_storage")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
logger.info("MCP Storage initialized")


@mcp.tool
def add_endpoint(endpoint: str, description: str) -> dict[str, Any]:
    """Register or update an MCP service endpoint into MCP Registry; tools are auto-discovered.

    Args:
        endpoint: The MCP server endpoint/URL.
        description: Brief human readable description for this service.

    Returns: The created/updated service with tools.
    """
    logger.info("add_endpoint called", extra={"endpoint": endpoint})
    with SessionLocal() as db:
        service = crud.create_or_update_service(
            db, endpoint=endpoint, description=description
        )
        payload = _service_to_dict(service)
        logger.info(
            "add_endpoint succeeded",
            extra={"service_id": service.id, "tools_count": len(service.tools)},
        )
        return payload


@mcp.tool
def list_services() -> list[dict[str, str]]:
    """List stored MCP services in the MCP Registry.

    Returns:
        List of services with their endpoint and description.
    """
    with SessionLocal() as db:
        items = crud.list_services_brief(db)
        logger.info("list_services returned", extra={"count": len(items)})
        return items


@mcp.tool
def remove_service(service_id: int) -> bool:
    """Remove a stored MCP service by id from MCP Registry"""
    logger.info("remove_service called", extra={"service_id": service_id})
    with SessionLocal() as db:
        ok = crud.delete_service(db, service_id)
        logger.info(
            "remove_service result", extra={"service_id": service_id, "deleted": ok}
        )
        return ok


@mcp.tool
def get_tools(
    service_id: int | None = None, endpoint: str | None = None
) -> list[dict[str, Any]]:
    """Return stored tools for a MCP service in the MCP Registry identified by id or endpoint."""
    logger.info(
        "get_tools called",
        extra={"service_id": service_id, "endpoint": endpoint},
    )
    with SessionLocal() as db:
        tools = crud.get_tools(db, service_id=service_id, endpoint=endpoint)
        items = [
            {"id": t.id, "name": t.name, "description": t.description} for t in tools
        ]
        logger.info("get_tools returned", extra={"count": len(items)})
        return items


def _service_to_dict(service) -> dict[str, Any]:
    return {
        "id": service.id,
        "endpoint": service.endpoint,
        "description": service.description,
        "tools": [
            {"id": t.id, "name": t.name, "description": t.description}
            for t in service.tools
        ],
    }


if __name__ == "__main__":
    # Default run method; FastMCP decides transport from env/cli
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    logger.info("Starting MCP server", extra={"host": host, "port": port})
    mcp.run(
        transport="http",
        host=host,
        port=port,
        reload=True,
        log_level="info",
        log_level_console="info",
        log_level_file="info",
    )
