# MCP Storage Server

A FastAPI-based HTTP MCP registry that stores other MCP service endpoints, descriptions, and their available tools. Provides MCP tools to manage this storage.

## Features

- Register MCP services by endpoint and description. Tools are discovered automatically.
- List stored MCP endpoints with their tool metadata.
- Remove a stored MCP service by id.

## Tech Stack

- FastAPI
- SQLAlchemy
- httpx
- In-memory MySQL via `sqlite` for dev; switchable to MySQL/PostgreSQL via env

## Quickstart

1. Install deps using uv:

   ```sh
   uv sync
   ```

2. Run the MCP server (FastMCP):

   ```sh
   uv run python -m mcp_storage.mcp_server
   # or
   uv run python -m mcp_storage
   ```

   For FastMCP HTTP/SSE transport options, follow FastMCP docs.

## Environment

Provide `DATABASE_URL` to switch DB engine. Examples:

- SQLite (default, dev): `sqlite+aiosqlite:///./dev.db`
- MySQL: `mysql+pymysql://user:pass@host:3306/dbname`
- PostgreSQL: `postgresql+psycopg://user:pass@host:5432/dbname`

## MCP Tools Exposed

- `add_endpoint(endpoint: str, description: str) -> service`: Registers/updates a service; tools auto-discovered
- `list_endpoints() -> list[service]`: Lists stored services with tools
- `remove_service(service_id: int) -> bool`: Removes a service by id
- `remove_tool(tool_id: int) -> bool`: Removes a single tool by id

Discovery logic uses `fastmcp.Client` in `mcp_storage/discovery.py`.

