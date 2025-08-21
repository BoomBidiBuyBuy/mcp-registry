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
   uv run python --env-file .env src/main.py
   ```

   It runs HTTP MCP server.

## Environment

Provide `DATABASE_URL` to switch DB engine. Examples:

- SQLite (default, dev): `sqlite+aiosqlite:///./dev.db`
- MySQL: `mysql+pymysql://user:pass@host:3306/dbname`
- PostgreSQL: `postgresql+psycopg://user:pass@host:5432/dbname`

## MCP Tools Exposed

- `add_endpoint(service_name: str, endpoint: str, description: str, requires_authorization: bool, method_authorization: str)`: Registers/updates a service; tools auto-discovered. The first parameter `service_name` is required and must be unique. Description comes from the `service_description` resource defined on the new MCP service.
- `list_services() -> list[service]`: Lists stored services with the description
- `remove_service(service_name: str) -> bool`: Removes a service by unique name
- `authorize_user_to_service(service_name: str, user_id: str, token: str)`: Allows user to set access token for a service.

Discovery logic uses `fastmcp.Client` in `mcp_storage/discovery.py`.

### Example: Add an endpoint that requires authorization

When a service requires authorization, provide the authorization method. Allowed values: `Basic` or `Bearer`.

```json
{
  "service_name": "svc1",
  "endpoint": "http://localhost:8000",
  "description": "My authorized MCP service",
  "requires_authorization": true,
  "method_authorization": "Basic"
}
```

If `requires_authorization` is false, `method_authorization` is ignored and stored as an empty string.


## HTTP Endpoints

### Health check

- Method: GET
- Path: `/health`
- 200 Response:

```json
{"status": "healthy", "service": "mcp-server"}
```

### Get token for a user and service

- Method: GET
- Path: `/token`
- Request body (JSON): note the current implementation expects a JSON body even for GET

```json
{"service_name": "<service-name>", "user_id": "<user-id>"}
```

- Responses:
  - 200:

    ```json
    {"token": "<token>", "method_authorization": "Bearer"}
    ```

  - 400: missing `service_name` or `user_id`
  - 401: user is not authorized for the service
  - 404: service not found

This endpoint lets an agent retrieve the stored token and authorization method for a given `user_id` and `service_name`, so it can construct the `Authorization` header for downstream tool calls.

## Authorization flow example

1. Admin adds service "pizza delivery" with `requires_authorization=true` and `method_authorization="Bearer"` using `add_service`.
2. A user connects their agent to the MCP Registry.
3. The user asks the agent to order a pizza.
4. The agent lists available services via `list_services`, finds "pizza delivery", inspects tools, and plans execution.
5. Before calling the external tool, the agent performs a pre-flight HTTP request to the MCP Registry:
   - GET `/token` with body `{ "service_name": "pizza-delivery", "user_id": "<user-id>" }` to check if authorization is available.
   - If 200, it receives `{ token, method_authorization }` and constructs `Authorization: Bearer <token>` (or `Basic <token>` depending on the method).
6. If the downstream tool call returns 401 Unauthorized, the agent calls the MCP tool `authorize_user_to_service`.
7. Using human-in-the-loop, the agent asks the user for their token. The agent then calls `authorize_user_to_service(service_name, user_id, token)` to save it in the MCP Registry and informs the user to repeat the request.
8. The user repeats: "order a pizza".
9. The agent again calls GET `/token` for the same `service_name` and `user_id`, receives the token and method, sets the `Authorization` header accordingly, and executes the planned tool call.
10. The tool call proceeds with proper authorization.

