# Services management

This document describes how to add, list, and remove MCP services in the MCP Registry, and how agents can discover available services and tools.

## List services

There are three ways to list services and tools:

1. MCP tool `list_services()`
   - Returns a list of dictionaries: `{ service_name, endpoint, description }`.
   - Typical use cases:
     - Admins connect directly to the MCP Registry to manage services.
     - An agent lists services to find candidates that might contain a needed tool.

2. MCP tool `get_tools(service_name)`
   - Returns tools for the specified service, including `id`, `name`, `description`, and allowed `roles`.

3. HTTP endpoint `GET /list_services`
   - Returns `{ "services": { "<service_name>": { "transport": "streamable_http", "url": "<endpoint>" } } }`.
   - Intended for agents to fetch available services and refresh local service catalogs.

## Add a service

Use the MCP tool `add_service` to register a new remote MCP endpoint. Tools are auto‑discovered.

Call:

- `add_service(service_name, endpoint, description, requires_authorization, method_authorization="")`

Parameters:

- `service_name` (str): Unique name for the service.
- `endpoint` (str): The MCP endpoint URL.
- `description` (str): A human‑readable description. If omitted/empty, the registry attempts to read the `service_description` resource from the remote service.
- `requires_authorization` (bool): Whether downstream calls require authorization.
- `method_authorization` (str): When authorization is required, one of `Basic` or `Bearer`. Ignored otherwise.

Behavior:

- The registry connects to the remote endpoint and discovers tools.
- The service is stored with its tools.
- If `AGENT_REREAD_HOOK` is configured, a GET request is sent to prompt the agent to refresh its service list.

Errors:

- If a service with the same `service_name` already exists, the call fails.
- If discovery fails, an error is returned.

## Remove a service

Use the MCP tool `remove_service(service_name)` to remove a stored service by unique name.

Behavior:

- Removes the service and all associated tools.
- If `AGENT_REREAD_HOOK` is configured, a GET request is sent to prompt the agent to refresh its service list.

Verification:

- Call `list_services()` to confirm the service is gone.
