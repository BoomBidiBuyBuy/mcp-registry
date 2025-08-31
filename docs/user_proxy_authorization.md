# User proxy-authorization

This document describes how a user provides credentials to the MCP Registry for a specific service, and how an agent retrieves those credentials to call downstream tools.

## Concepts

- Some services require authorization (e.g., Bearer token or Basic auth).
- The registry stores a per-user token for a given `service_name` when authorization is required.
- The authorization method is configured on the service when it is added (`requires_authorization`, `method_authorization`).

## Set a token via MCP tool

Use `authorize_user_to_service(service_name, user_id, token)` to save/update the token for a user.

Behavior:

- Ensures the `user_id` exists; creates the user if missing.
- Validates that the `service_name` exists.
- Stores or updates the token for that `(user, service)` pair.

Example call:

```json
{
  "service_name": "orders-api",
  "user_id": "alice",
  "token": "<secret>"
}
```

The tool returns a confirmation message.

## Retrieve a token via HTTP

Agents should call `GET /token` with a JSON body to retrieve the token and the authorization method for a user and service:

- Method: GET
- Path: `/token`
- JSON body: `{ "service_name": "<service>", "user_id": "<user>" }`

Responses:

- 200 OK (service requires authorization and token exists):
  ```json
  { "token": "<token>", "method_authorization": "Bearer" }
  ```
- 200 OK (service does not require authorization):
  ```json
  { "status": "Ok" }
  ```
- 400: missing `service_name` or `user_id`.
- 401: user is not authorized for the service (no token stored).
- 404: service not found.

## Typical agent flow

1. User asks to use a tool from a service that requires auth.
2. Agent calls `GET /token` with `service_name` and `user_id`.
3. If 200 with `{ token, method_authorization }`, construct the `Authorization` header and proceed.
4. If 401, the agent requests the user’s token and calls `authorize_user_to_service(...)` to store it.
5. Repeat step 2, then continue with the planned tool call.
