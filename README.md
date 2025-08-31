# MCP Registry (Storage Server)

A FastAPI-based MCP Registry that stores MCP service endpoints, descriptions, and their discovered tools. It exposes MCP tools and HTTP endpoints for service discovery, authorization, and role-based access management.

## Features

- Register MCP services by endpoint and description; tools are discovered automatically.
- List stored MCP services with their tool metadata.
- Remove a stored MCP service by unique name.
- Manage roles and attach/detach them to tools for role-based access.
- Store per-user authorization tokens for services; agents can fetch them via HTTP.

## Tech Stack

- FastAPI
- SQLAlchemy
- httpx
- SQLite for development; switchable to MySQL/PostgreSQL via environment variables.

## Quickstart

1. Install deps using uv:

   ```sh
   uv sync
   ```

2. Run the MCP server (FastMCP over HTTP):

   ```sh
   uv run python --env-file .env src/main.py
   ```

   This starts the MCP server over HTTP.

## Environment

Environment variables:

- `DATABASE_URL`: switch DB engine. Examples:

- SQLite (default, dev): `sqlite+aiosqlite:///./dev.db`
- MySQL: `mysql+pymysql://user:pass@host:3306/dbname`
- `MCP_HOST` (default `0.0.0.0`) and `MCP_PORT` (default `8000`) control the HTTP listener.
- Optional `AGENT_REREAD_HOOK`: if set, the registry will call this URL via GET after adding/removing services, prompting agents to refresh their catalogs.

## MCP Tools Exposed

- Services
  - `add_service(service_name: str, endpoint: str, description: str, requires_authorization: bool, method_authorization: str="")` — Register a service; tools auto-discovered. If `description` is empty, the registry tries to read the `service_description` resource from the remote service. Fails if `service_name` already exists.
  - `list_services() -> list[dict]` — List `{ service_name, endpoint, description }`.
  - `get_tools(service_name: str) -> list[dict]` — List tools for a service, including allowed `roles`.
  - `remove_service(service_name: str) -> str` — Remove a stored service by unique name.

- Authorization
  - `authorize_user_to_service(service_name: str, user_id: str, token: str)` — Store/update a user token for a service requiring authorization.

- Roles and users
  - `create_role(role_name: str, default_system_prompt: str = "")` / `remove_role(role_name: str)` / `list_roles() -> list[dict]`
  - `set_role_system_prompt(role_name: str, default_system_prompt: str)` — Update a role's default system prompt.
  - `list_roles` now returns objects like `{ "name": "<role>", "default_system_prompt": "..." }`.
  - `assign_role_to_user(user_id: str, role_name: str)` / `remove_role_from_user(user_id: str, role_name: str)` / `list_users() -> list[tuple[user_id, role]]`
  - `attach_role_to_tool(tool_id: int, role_name: str)` / `detach_role_from_tool(tool_id: int, role_name: str)`

Discovery logic uses `fastmcp.Client` in `src/discovery.py`.

### Example: Add a service that requires authorization

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
  - 200 (service requires authorization and token exists):

    ```json
    {"token": "<token>", "method_authorization": "Bearer"}
    ```

  - 200 (service does not require authorization): `{ "status": "Ok" }`
  - 400: missing `service_name` or `user_id`
  - 401: user is not authorized for the service
  - 404: service not found

This endpoint lets an agent retrieve the stored token and authorization method for a given `user_id` and `service_name`, so it can construct the `Authorization` header for downstream tool calls.

### List services for agents

- Method: GET
- Path: `/list_services`
- 200 Response:

```json
{
  "services": {
    "<service_name>": { "transport": "streamable_http", "url": "<endpoint>" }
  }
}
```

### Resolve role for a user

- Method: POST
- Path: `/role_for_user`
- Request body (JSON): `{ "user_id": "<user-id>" }`
- 200 Response:

```json
{ "role": "<role-name-or-empty>" }
```

### List tools available to a role

- Method: POST
- Path: `/tools_for_role`
- Request body (JSON): `{ "role": "<role-name>" }`
- 200 Response:

```json
{ "tools": [{ "id": 1, "name": "...", "description": "..." }] }
```

### Get default system prompt for a role

- Method: POST
- Path: `/system_prompt_for_role`
- Request body (JSON): `{ "role": "<role-name>" }`
- 200 Response:

```json
{ "default_system_prompt": "..." }
```

Agents can call this to extend their system prompt for users with the specified role.

## Authorization flow example

1. Admin adds service "pizza delivery" with `requires_authorization=true` and `method_authorization="Bearer"` using `add_service`.
2. A user connects their agent to the MCP Registry.
3. The user asks the agent to order a pizza.
4. The agent lists available services via `list_services`, finds "pizza delivery", inspects tools, and plans execution.
5. Before calling the external tool, the agent performs a pre-flight HTTP request to the MCP Registry:
   - GET `/token` with body `{ "service_name": "pizza-delivery", "user_id": "<user-id>" }` to check if authorization is available.
   - If 200 with `{ token, method_authorization }`, construct `Authorization: Bearer <token>` (or `Basic <token>` depending on the method).
   - If 200 with `{ "status": "Ok" }`, the service does not require authorization; continue without auth.
6. If the downstream tool call returns 401 Unauthorized, the agent calls the MCP tool `authorize_user_to_service`.
7. Using human-in-the-loop, the agent asks the user for their token. The agent then calls `authorize_user_to_service(service_name, user_id, token)` to save it in the MCP Registry and informs the user to repeat the request.
8. The user repeats: "order a pizza".
9. The agent again calls GET `/token` for the same `service_name` and `user_id`, receives the token and method, sets the `Authorization` header accordingly, and executes the planned tool call.
10. The tool call proceeds with proper authorization.

## Documentation

- Roles and users: `docs/roles_and_users.md`
- Roles and services (tool access): `docs/roles_and_services.md`
- Services management: `docs/services_management.md`
- User proxy-authorization: `docs/user_proxy_authorization.md`

