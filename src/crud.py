import logging

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

import models
from discovery import DiscoveryClient, DiscoveryError


logger = logging.getLogger(__name__)


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

    service_stmt = (
        select(models.MCPService)
        .options(
            # Eager-load tools and their attached roles to avoid detached lazy loads
            joinedload(models.MCPService.tools).joinedload(models.MCPTool.roles)
        )
        .where(models.MCPService.service_name == service_name)
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
        logger.info(f"User {user_id} does not exist, create a record")
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


# Roles CRUD


def create_role(db: Session, *, role_name: str) -> models.MCPRole:
    """Create a new role by unique name.

    Raises ValueError if role already exists.
    """
    stmt = select(models.MCPRole).where(models.MCPRole.name == role_name)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Role with name '{role_name}' already exists")
    role = models.MCPRole(name=role_name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def attach_role_to_tool(db: Session, *, role_name: str, tool_id: int) -> bool:
    """Attach an existing role to a tool.

    Returns True if attached, False if it was already attached.
    Raises ValueError if role or tool not found.
    """
    role = db.execute(
        select(models.MCPRole).where(models.MCPRole.name == role_name)
    ).scalar_one_or_none()
    if role is None:
        raise ValueError(f"Role with name '{role_name}' not found")

    tool = db.execute(
        select(models.MCPTool).where(models.MCPTool.id == tool_id)
    ).scalar_one_or_none()
    if tool is None:
        raise ValueError(f"Tool with id '{tool_id}' not found")

    if role in tool.roles:
        logger.info(f"Role {role_name} is already attached to tool {tool_id}")
        return False
    tool.roles.append(role)
    db.commit()
    return True


def detach_role_from_tool(db: Session, *, role_name: str, tool_id: int) -> bool:
    """Detach a role from a tool.

    Returns True if detached, False if it was not attached.
    Raises ValueError if role or tool not found.
    """
    role = db.execute(
        select(models.MCPRole).where(models.MCPRole.name == role_name)
    ).scalar_one_or_none()
    if role is None:
        raise ValueError(f"Role with name '{role_name}' not found")

    tool = db.execute(
        select(models.MCPTool).where(models.MCPTool.id == tool_id)
    ).scalar_one_or_none()
    if tool is None:
        raise ValueError(f"Tool with id '{tool_id}' not found")

    if role not in tool.roles:
        logger.info(f"Role {role_name} is not attached to tool {tool_id}")
        return False
    tool.roles.remove(role)
    db.commit()
    return True


def remove_role(db: Session, *, role_name: str) -> bool:
    """Remove a role by name; it is also removed from all tools.
    It is also removed from all users.

    Raises ValueError if role not found.
    """
    role = db.execute(
        select(models.MCPRole).where(models.MCPRole.name == role_name)
    ).scalar_one_or_none()
    if role is None:
        logger.info(f"Role {role_name} does not exist")
        raise ValueError(f"Role {role_name} does not exist")
    # Ensure association rows are cleared even if FK cascades are not enforced
    role.tools.clear()
    # Also unset from users holding this role
    for user in list(role.users):
        user.role = None
    db.delete(role)
    db.commit()
    return True


def list_tools_by_role(db: Session, *, role_name: str) -> list[models.MCPTool]:
    """List tools that can be used by the role.

    Returns empty list if role not found or has no tools.
    """
    role = db.execute(
        select(models.MCPRole).where(models.MCPRole.name == role_name)
    ).scalar_one_or_none()
    if role is None:
        return []
    # Access relationship to ensure load
    _ = role.tools  # noqa: F841
    return list(role.tools)


def get_role_for_user(db: Session, *, user_id: str) -> models.MCPRole | None:
    """Return the role for a user.

    Returns None if user not found or has no role.
    """
    user = db.execute(
        select(models.MCPUser).where(models.MCPUser.user_id == user_id)
    ).scalar_one_or_none()
    if user is None:
        return None
    return user.role


def assign_role_to_user(db: Session, *, user_id: str, role_name: str) -> bool:
    user = db.execute(
        select(models.MCPUser).where(models.MCPUser.user_id == user_id)
    ).scalar_one_or_none()
    if user is None:
        logger.info(f"User {user_id} does not exist, create a record")
        raise ValueError(f"User {user_id} does not exist, create a record")
    role = db.execute(
        select(models.MCPRole).where(models.MCPRole.name == role_name)
    ).scalar_one_or_none()
    if role is None:
        logger.info(f"Role {role_name} does not exist")
        raise ValueError(f"Role {role_name} does not exist")
    user.role = role
    db.commit()
    return True


def remove_role_from_user(db: Session, *, user_id: str, role_name: str) -> bool:
    user = db.execute(
        select(models.MCPUser).where(models.MCPUser.user_id == user_id)
    ).scalar_one_or_none()
    if user is None:
        logger.info(f"User {user_id} does not exist")
        raise ValueError(f"User {user_id} does not exist")
    if user.role is None:
        logger.info(f"User {user_id} does not have a role")
    user.role = None
    db.commit()
    return True


def list_users(db: Session) -> list[models.MCPUser]:
    """List all users with roles eagerly loaded to avoid detached lazy loads."""
    return (
        db.execute(select(models.MCPUser).options(joinedload(models.MCPUser.role)))
        .scalars()
        .all()
    )


def list_roles(db: Session) -> list[models.MCPRole]:
    """List all roles."""
    return db.execute(select(models.MCPRole)).scalars().all()


# Re-export new APIs
__all__ += [
    "create_role",
    "attach_role_to_tool",
    "detach_role_from_tool",
    "remove_role",
    "list_tools_by_role",
    "get_role_for_user",
    "list_roles",
]
