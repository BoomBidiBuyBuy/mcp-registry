# Roles and services

This document explains how roles interact with services and tools in the MCP Registry.

- A service represents a remote MCP server that exposes tools.
- Each service contains one or more tools discovered automatically from the remote endpoint.
- Roles can be attached to tools to allow only specific users (by role) to use them.

Tools returned by `get_tools(service_name)` include a `roles` field listing which roles are allowed to use each tool. If no roles are attached to a tool, it is considered available to any role.

## Prerequisites

- You have added a service using `add_service(...)`.
- You know the `service_name` and can list its tools with `get_tools(service_name)`.
- The role you want to use already exists (create with `create_role(role_name)`).

## Attach a role to a tool

Attaching a role to a tool restricts usage of that tool to users who have that role.

1. List tools for the service:
   - Call `get_tools(service_name)` and find the target tool `id`.
2. Attach the role:
   - Call `attach_role_to_tool(tool_id=<id>, role_name=<role>)`.
3. Verify:
   - Call `get_tools(service_name)` again and check that the tool now includes the role in its `roles` list.

Notes:
- If the role or tool does not exist, the command fails with an error.
- If the role is already attached, the operation succeeds with no changes.

## Detach a role from a tool

Detaching a role removes that role’s access to the tool.

1. List tools and confirm the role is present on the tool.
2. Call `detach_role_from_tool(tool_id=<id>, role_name=<role>)`.
3. Verify with `get_tools(service_name)` that the role is no longer listed for the tool.

Notes:
- If the role is not attached to the tool, the operation is a no‑op.
- Removing a role from a tool does not delete the role itself or affect users’ other permissions.

## How enforcement works

- The MCP Registry stores the mapping of tools to allowed roles.
- An agent can query:
  - `POST /role_for_user` to resolve a user’s role by `user_id`.
  - `POST /tools_for_role` to fetch tools available to a specific role.
- The agent should use these APIs to plan which tools the user may invoke.
