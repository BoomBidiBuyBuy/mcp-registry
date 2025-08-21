from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from fastmcp import Context

import models
from discovery import DiscoveryClient, DiscoveryError


async def create_or_update_service(
    db: Session,
    endpoint: str,
    description: str,
    requires_authorization: bool,
    context: Context,
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

    # Check if service exists
    result = db.execute(
        select(models.MCPService).where(models.MCPService.endpoint == str(endpoint))
    )
    service = result.scalar_one_or_none()

    if service is None:
        service = models.MCPService(
            endpoint=str(endpoint),
            description=description,
            requires_authorization=requires_authorization,
        )
        db.add(service)
        db.flush()  # populate service.id for tool FK
    else:
        service.description = description
        service.requires_authorization = requires_authorization
        # Remove existing tools to replace with refreshed ones
        db.execute(
            delete(models.MCPTool).where(models.MCPTool.service_id == service.id)
        )

    # Insert tools
    for t in tools:
        db.add(
            models.MCPTool(
                service_id=service.id,
                name=t["name"],
                description=t.get("description", ""),
            )
        )

    db.commit()
    db.refresh(service)
    return service


def list_services(db: Session) -> list[models.MCPService]:
    result = db.execute(select(models.MCPService))
    services = result.scalars().unique().all()
    # Eagerly load tools by touching attribute
    for s in services:
        _ = s.tools  # noqa: F841
    return services


def delete_service(db: Session, service_id: int) -> bool:
    # Delete service and cascade tools
    result = db.execute(
        select(models.MCPService).where(models.MCPService.id == service_id)
    )
    service = result.scalar_one_or_none()
    if service is None:
        return False
    db.delete(service)
    db.commit()
    return True


def delete_tool(db: Session, tool_id: int) -> bool:
    result = db.execute(select(models.MCPTool).where(models.MCPTool.id == tool_id))
    tool = result.scalar_one_or_none()
    if tool is None:
        return False
    db.delete(tool)
    db.commit()
    return True


def list_services_brief(db: Session) -> list[dict[str, str]]:
    """Return only endpoint and description for all services."""
    result = db.execute(
        select(models.MCPService.endpoint, models.MCPService.description)
    )
    return [
        {"endpoint": endpoint, "description": description}
        for endpoint, description in result.all()
    ]


def get_tools(
    db: Session,
    *,
    service_id: int,
) -> list[models.MCPTool]:
    """Return tools stored for a service, identified by id."""

    service_stmt = select(models.MCPService).where(models.MCPService.id == service_id)

    service = db.execute(service_stmt).scalar_one_or_none()
    if service is None:
        return []
    # Access relationship to ensure load
    _ = service.tools  # noqa: F841
    return list(service.tools)


__all__ = [
    "create_or_update_service",
    "list_services",
    "list_services_brief",
    "delete_service",
    "delete_tool",
    "get_tools",
    "DiscoveryError",
]
