# Roles and users

This document explains how users and roles are modeled and managed in the MCP Registry, and how an agent should resolve what tools a user can access.

## Data model

- User: a registered user in the MCP Registry, identified by external `user_id`. A user can have at most one role.
- Role: a named permission label used to allow/deny access to tools. Role has a unique `name`.
- Service: a remote MCP service with unique `service_name`, `endpoint`, and `description`.
- Tool: an MCP tool discovered under a `Service`. Each tool has a `name`, `description`, and optional list of allowed `roles`.

## How users are created

Users are created on demand when the agent first references a `user_id`:

1. The agent needs to determine the user's role or set a token.
2. The MCP Registry receives the request and ensures the user exists (`get_or_create_user`).
3. If the user did not exist, it is created with no role assigned.

Notes:
- A user with no role can still interact with the agent, but access to tools may be limited by role enforcement.

## Create a role

Use this when you need a new permission label.

1. Call `create_role(role_name)`.
2. If the role already exists, an error is returned.

## Assign a role to a user

1. Ensure the user exists (triggered automatically by calling APIs with `user_id`).
2. List users to verify current assignments: `list_users()`.
3. Assign the role: `assign_role_to_user(user_id=<id>, role_name=<role>)`.
4. Verify with `list_users()` that the new role is shown.

Errors:
- If the `role_name` does not exist or `user_id` is unknown, an error is returned.

## Remove a role from a user

1. List users and confirm the user has a role.
2. Call `remove_role_from_user(user_id=<id>, role_name=<role>)`.
3. Verify with `list_users()` that the user now has no role.

Notes:
- If the user has no role, the operation is effectively a no‑op.

## Remove a role

Removes the role entity and cleans up references.

1. Call `remove_role(role_name=<role>)`.
2. Internally, the role is removed from all tools and unset from all users.
3. Verify with `list_users()` and `get_tools(service_name)` that the role is no longer present.

Errors:
- If the role does not exist, an error is returned.

## List roles

Use `list_roles()` to retrieve the list of role names.

## Agent integration: resolving allowed tools for a user

An agent can resolve available tools for a specific `user_id` via HTTP routes:

- `POST /role_for_user` with body `{ "user_id": "<user-id>" }` returns `{ "role": "<role-name>" }` or an empty string if none.
- `POST /tools_for_role` with body `{ "role": "<role-name>" }` returns `{ "tools": [{ id, name, description }] }`.

With this, the agent can determine which tools to plan and invoke for the user.