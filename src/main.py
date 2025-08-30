from typing import Any, Annotated
import logging
import asyncio
import httpx

from starlette.requests import Request
from starlette.responses import JSONResponse
from fastmcp import FastMCP
from fastapi import HTTPException

from storage import get_engine_and_sessionmaker, init_db, get_db_session
import crud
import envs


mcp_server = FastMCP(
    name="mcp-storage",
    instructions="The MCP registry that stores other MCP service endpoints, descriptions, and their available tools. Allows to manage them",
)

engine, SessionLocal = get_engine_and_sessionmaker()
init_db(engine)
get_db = get_db_session(SessionLocal)

# Configure logging
logger = logging.getLogger("mcp_storage")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
logger.info("MCP Storage initialized")


@mcp_server.custom_route("/token", methods=["GET"])
def http_get_token(request: Request):
    logger.info("http_get_token called")
    data = request.json()
    service_name = data.get("service_name", "")
    user_id = data.get("user_id", "")
    if service_name == "" or user_id == "":
        raise HTTPException(
            status_code=400, detail="service_name and user_id are required"
        )

    logger.info(f"http_get_token called service_name={service_name}, user_id={user_id}")

    with SessionLocal() as db:
        # If service does not require authorization, return 200 OK without token
        requires_auth = crud.get_service_requires_authorization(
            db, service_name=service_name
        )
        if requires_auth is None:
            raise HTTPException(status_code=404, detail="Service not found")
        if requires_auth is False:
            return JSONResponse({"status": "Ok"})

        token = crud.get_user_service_token(
            db, user_id=user_id, service_name=service_name
        )
        if token is None:
            raise HTTPException(
                status_code=401,
                detail="User is not authorized to use this service. Authroize please.",
            )
        method = crud.get_service_auth_method(db, service_name=service_name)
        if method is None:
            raise HTTPException(status_code=404, detail="Service not found")
        logger.info(
            f"http_get_token returned token={token}, method_authorization={method}"
        )
        return JSONResponse({"token": token, "method_authorization": method})


@mcp_server.custom_route("/health", methods=["GET"])
async def http_health_check(request):
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


@mcp_server.custom_route("/role_for_user", methods=["GET"])
async def http_role_for_user(request: Request):
    logger.info("http_role_for_user called")
    data = request.json()
    user_id = data.get("user_id", "")
    if user_id == "":
        raise HTTPException(status_code=400, detail="user_id is required")

    with SessionLocal() as db:
        role = crud.get_role_for_user(db, user_id=user_id)
        if role is None:
            raise HTTPException(status_code=404, detail="Role not found")

    return JSONResponse({"role": role.name})


@mcp_server.custom_route("/tools_for_role", methods=["POST"])
async def http_tools_for_role(request: Request):
    logger.info("http_tools_for_role called")
    data = request.json()
    role_name = data.get("role", "")
    if role_name == "":
        raise HTTPException(status_code=400, detail="role is required")
    with SessionLocal() as db:
        tools = crud.get_tools_for_role(db, role_name=role_name)
        if tools is None:
            raise HTTPException(status_code=404, detail="Tools not found")
    return JSONResponse({"tools": tools})


@mcp_server.tool(tags=["admin"])
async def add_service(
    service_name: Annotated[str, "Unique service name"],
    endpoint: Annotated[str, "The MCP server endpoint/URL."],
    description: Annotated[str, "The MCP service used specified description"],
    requires_authorization: Annotated[
        bool, "Whether this service requires authorization"
    ],
    method_authorization: Annotated[
        str,
        "Authorization method when requires_authorization is True. Allowed: 'Basic' or 'Bearer'",
    ] = "",
) -> Annotated[str, "The created/updated service with tools."]:
    """Register or update an MCP service endpoint into MCP Registry; tools are auto-discovered from the service."""
    logger.info(f"add_service called service_name={service_name} endpoint={endpoint}")
    with SessionLocal() as db:
        service = await crud.create_or_update_service(
            db,
            service_name=service_name,
            endpoint=endpoint,
            description=description,
            requires_authorization=requires_authorization,
            method_authorization=method_authorization,
        )

        logger.info(
            f"add_service succeeded service_name={service.service_name}, tools_count={len(service.tools)}"
        )

        # reread hook
        if envs.AGENT_REREAD_HOOK:
            logger.info("Let know agent that we have new service")
            with httpx.get(envs.AGENT_REREAD_HOOK) as response:
                response.raise_for_status()
                logger.info(f"Agent reread hook called response={response.text}")

        # return only breif output to not littering into the context
        return f"Create service with name='{service.service_name}'"


@mcp_server.tool
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


@mcp_server.custom_route("/list_services", methods=["GET"])
def http_list_services(request: Request):
    logger.info("http_list_services called")
    with SessionLocal() as db:
        services = crud.list_services_brief(db)
        result = {
            service["service_name"]: {
                "transport": "streamable_http",
                "url": service["endpoint"],
            }
            for service in services
        }
        return JSONResponse({"services": result})


@mcp_server.tool(tags=["admin"])
def remove_service(
    service_name: Annotated[str, "The MCP service name to remove"],
) -> Annotated[str, "Status message of the operation"]:
    """Remove a stored MCP service by unique name from MCP Registry"""
    logger.info(f"remove_service called service_name={service_name}")
    with SessionLocal() as db:
        crud.delete_service(db, service_name)
        logger.info(f"remove_service result service_name={service_name}")

        # reread hook
        if envs.AGENT_REREAD_HOOK:
            logger.info("Let know agent that we have removed service")
            with httpx.get(envs.AGENT_REREAD_HOOK) as response:
                response.raise_for_status()
                logger.info(f"Agent reread hook called response={response.text}")

        return f"Service with name='{service_name}' removed"


@mcp_server.tool
def get_tools(service_name: str) -> list[dict[str, Any]]:
    """Return stored tools for a MCP service in the MCP Registry identified by unique service name."""
    logger.info(f"get_tools called service_name={service_name}")
    with SessionLocal() as db:
        tools = crud.get_tools(db, service_name=service_name)
        items = [
            {"id": t.id, "name": t.name, "description": t.description} for t in tools
        ]
        logger.info(f"get_tools returned count={len(items)}")
        return items


@mcp_server.tool
def authorize_user_to_service(
    service_name: Annotated[str, "The MCP service name to authorize the user for"],
    user_id: Annotated[str, "The user identifier to be authorized"],
    token: Annotated[
        str, "The authorization token to associate with the user for the service"
    ],
) -> Annotated[str, "Status message of the authorization operation"]:
    """Authorize a user for a specific MCP service by setting an authorization token."""
    logger.info(
        f"authorize_user_to_service called service_name={service_name}, user_id={user_id}"
    )
    with SessionLocal() as db:
        # Ensure user exists; create if not
        crud.get_or_create_user(db, user_id=user_id)
        crud.set_user_service_token(
            db, user_id=user_id, service_name=service_name, token=token
        )
    return "Authorization token is set, please repeat your original request"


if __name__ == "__main__":
    # Default run method; FastMCP decides transport from env/cli
    host = envs.MCP_HOST
    port = int(envs.MCP_PORT)
    logger.info(f"Starting MCP server host={host}, port={port}")
    asyncio.run(mcp_server.run_async(transport="http", host=host, port=port))
