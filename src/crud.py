from sqlalchemy.orm import Session
from sqlalchemy import select

import models
from discovery import DiscoveryClient, DiscoveryError


async def create_or_update_service(
    db: Session,
    service_name: str,
    endpoint: str,
    description: str,
    requires_authorization: bool,
    method_authorization: str,
    #    context: Context,
) -> models.MCPService:
    # Discover tools from endpoint
    client = DiscoveryClient()
    tools = await client.fetch_tools(str(endpoint))
    if not description:
        description = await client.fetch_description(str(endpoint))
        if description is None:
            description = "No description found, list tools to get more information"

        # if description is None:
        #    # TODO: in case of failure we can implement generated description using the sampling feature
        #    # and the tools description
        #    # It might failt because server doesn't support elicit feature
        #    description = await context.elicit(
        #        "Please provide a description for the MCP service",
        #        response_type=str,
        #    )

    # Check if service exists by unique service_name
    result = db.execute(
        select(models.MCPService).where(
            models.MCPService.service_name == str(service_name)
        )
    )
    service = result.scalar_one_or_none()

    # Ensure method is only persisted when authorization is required
    if not requires_authorization:
        method_authorization = ""

    if service is None:
        service = models.MCPService(
            service_name=service_name,
            endpoint=endpoint,
            description=description,
            requires_authorization=requires_authorization,
            method_authorization=method_authorization,
        )
        db.add(service)
    else:
        raise ValueError(f"Service with name '{service_name}' already exists")

    # Insert tools
    for t in tools:
        db.add(
            models.MCPTool(
                service_name=service.service_name,
                name=t["name"],
                description=t.get("description", ""),
            )
        )

    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service_name: str) -> bool:
    # Delete service and cascade tools
    result = db.execute(
        select(models.MCPService).where(models.MCPService.service_name == service_name)
    )
    service = result.scalar_one_or_none()
    if service is None:
        return False
    db.delete(service)
    db.commit()
    return True


def list_services_brief(db: Session) -> list[dict[str, str]]:
    """Return only endpoint and description for all services."""
    result = db.execute(
        select(
            models.MCPService.service_name,
            models.MCPService.endpoint,
            models.MCPService.description,
        )
    )
    return [
        {"service_name": service_name, "endpoint": endpoint, "description": description}
        for service_name, endpoint, description in result.all()
    ]


def get_tools(
    db: Session,
    *,
    service_name: str,
) -> list[models.MCPTool]:
    """Return tools stored for a service, identified by unique service_name."""

    service_stmt = select(models.MCPService).where(
        models.MCPService.service_name == service_name
    )

    service = db.execute(service_stmt).scalar_one_or_none()
    if service is None:
        return []
    # Access relationship to ensure load
    _ = service.tools  # noqa: F841
    return list(service.tools)


def get_or_create_user(db: Session, *, user_id: str) -> models.MCPUser:
    stmt = select(models.MCPUser).where(models.MCPUser.user_id == user_id)
    user = db.execute(stmt).scalar_one_or_none()
    if user is None:
        user = models.MCPUser(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def set_user_service_token(
    db: Session,
    *,
    user_id: str,
    service_name: str,
    token: str,
) -> models.UserAccessToken:
    """Create or update a user's access token for the given service.

    Ensures one token per (user, service) pair.
    """
    # Ensure service exists (by service_name)
    service_stmt = select(models.MCPService).where(
        models.MCPService.service_name == service_name
    )
    service = db.execute(service_stmt).scalar_one_or_none()
    if service is None:
        raise ValueError(f"Service with name '{service_name}' not found")

    user = get_or_create_user(db, user_id=user_id)

    token_stmt = select(models.UserAccessToken).where(
        models.UserAccessToken.user_id_fk == user.id,
        models.UserAccessToken.service_name == service_name,
    )
    existing = db.execute(token_stmt).scalar_one_or_none()
    if existing is None:
        existing = models.UserAccessToken(
            user_id_fk=user.id, service_name=service_name, token=token
        )
        db.add(existing)
    else:
        existing.token = token

    db.commit()
    db.refresh(existing)
    return existing


def get_user_service_token(
    db: Session,
    *,
    user_id: str,
    service_name: str,
) -> str | None:
    """Return token for the given user and service_name, or None if missing."""
    stmt_user = select(models.MCPUser).where(models.MCPUser.user_id == user_id)
    user = db.execute(stmt_user).scalar_one_or_none()
    if user is None:
        return None

    stmt = select(models.UserAccessToken.token).where(
        models.UserAccessToken.user_id_fk == user.id,
        models.UserAccessToken.service_name == service_name,
    )
    row = db.execute(stmt).first()
    return row[0] if row else None


def get_service_auth_method(
    db: Session,
    *,
    service_name: str,
) -> str | None:
    """Return authorization method configured for a service ("Basic", "Bearer" or "").

    Returns None if the service does not exist.
    """
    stmt = select(models.MCPService.method_authorization).where(
        models.MCPService.service_name == service_name
    )
    row = db.execute(stmt).first()
    return row[0] if row else None


def get_service_requires_authorization(
    db: Session,
    *,
    service_name: str,
) -> bool | None:
    """Return whether a service requires authorization.

    Returns None if the service does not exist.
    """
    stmt = select(models.MCPService.requires_authorization).where(
        models.MCPService.service_name == service_name
    )
    row = db.execute(stmt).first()
    return row[0] if row else None


__all__ = [
    "create_or_update_service",
    "list_services_brief",
    "delete_service",
    "get_tools",
    "get_or_create_user",
    "set_user_service_token",
    "get_user_service_token",
    "get_service_auth_method",
    "get_service_requires_authorization",
    "DiscoveryError",
]
