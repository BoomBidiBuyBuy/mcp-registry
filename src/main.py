from typing import Any, Annotated
import logging
import asyncio

from fastmcp import FastMCP, Context

from storage import get_engine_and_sessionmaker, init_db
import crud
import envs


mcp_server = FastMCP(
    name="mcp-storage",
    instructions="The MCP registry that stores other MCP service endpoints, descriptions, and their available tools. Allows to manage them",
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


@mcp_server.tool(tags=["admin"])
async def add_endpoint(
    endpoint: Annotated[str, "The MCP server endpoint/URL."],
    description: Annotated[str, "The MCP service used specified description"],
    context: Context,
) -> Annotated[str, "The created/updated service with tools."]:
    """Register or update an MCP service endpoint into MCP Registry; tools are auto-discovered from the service."""
    logger.info(f"add_endpoint called endpoint={endpoint}")
    with SessionLocal() as db:
        service = await crud.create_or_update_service(
            db, endpoint=endpoint, description=description, context=context
        )

        logger.info(
            f"add_endpoint succeeded service_id={service.id}, tools_count={len(service.tools)}"
        )
        # return only breif output to not littering into the context
        return f"Create service with id='{service.id}'"


@mcp_server.tool(tags=["admin"])
def list_services() -> Annotated[
    list[dict[str, str]], "List of services with their endpoint and description."
]:
    """List stored MCP services in the MCP Registry.
    Helpful when need to find services that serve necessary tool.
    """
    with SessionLocal() as db:
        items = crud.list_services_brief(db)
        logger.info(f"list_services returned count={len(items)}")
        return items


@mcp_server.tool(tags=["admin"])
def remove_service(
    service_id: Annotated[str, "The MCP service id to remove"],
) -> Annotated[str, "Status message of the operation"]:
    """Remove a stored MCP service by id from MCP Registry"""
    logger.info(f"remove_service called service_id={service_id}")
    with SessionLocal() as db:
        crud.delete_service(db, service_id)
        logger.info(f"remove_service result service_id={service_id}")
        return f"Service with id='{service_id}' removed"


@mcp_server.tool
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
        logger.info(f"get_tools returned count={len(items)}")
        return items


if __name__ == "__main__":
    # Default run method; FastMCP decides transport from env/cli
    host = envs.MCP_HOST
    port = int(envs.MCP_PORT)
    logger.info(f"Starting MCP server host={host}, port={port}")
    asyncio.run(mcp_server.run_async(transport="http", host=host, port=port))
