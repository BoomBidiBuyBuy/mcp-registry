import logging
import asyncio

from fastmcp import FastMCP

from src.storage import get_engine_and_sessionmaker, init_db, get_db_session

import src.envs as envs


# Configure logging
logger = logging.getLogger("mcp_storage")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
logger.info("MCP Storage initialized")


engine, SessionLocal = get_engine_and_sessionmaker()
init_db(engine)
get_db = get_db_session(SessionLocal)


mcp_server = FastMCP(
    name="mcp-storage",
    instructions="The MCP registry that stores other MCP service endpoints, descriptions, and their available tools. Allows to manage them",
)


import http_endpoints  
import mcp_endpoints


http_endpoints.register(mcp_server)
mcp_endpoints.register(mcp_server)


if __name__ == "__main__":
    # Default run method; FastMCP decides transport from env/cli
    host = envs.MCP_HOST
    port = int(envs.MCP_PORT)
    logger.info(f"Starting MCP server host={host}, port={port}")
    asyncio.run(mcp_server.run_async(transport="http", host=host, port=port))
