from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from fastmcp import Context

import models
from discovery import DiscoveryClient, DiscoveryError


async def create_or_update_service(
    db: Session, endpoint: str, context: Context
) -> models.MCPService:
    # Discover tools from endpoint
    client = DiscoveryClient()
    tools = await client.fetch_tools(str(endpoint))
    description = await client.fetch_description(str(endpoint))
    if description is None:
        description = await context.elicit(
            "Please provide a description for the MCP service",
            response_type=str,
        )
        # TODO: in case of failure we can implement generated description using the sampling feature
        # and the tools description

    # Check if service exists
    result = db.execute(
        select(models.MCPService).where(models.MCPService.endpoint == str(endpoint))
    )
    service = result.scalar_one_or_none()

    if service is None:
        service = models.MCPService(endpoint=str(endpoint), description=description)
        db.add(service)
        db.flush()  # populate service.id for tool FK
    else:
        service.description = description
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
    service_id: int | None = None,
    endpoint: str | None = None,
) -> list[models.MCPTool]:
    """Return tools stored for a service, identified by id or endpoint.

    Exactly one of service_id or endpoint must be provided.
    """
    if (service_id is None and endpoint is None) or (
        service_id is not None and endpoint is not None
    ):
        raise ValueError("Provide exactly one of service_id or endpoint")

    if service_id is not None:
        service_stmt = select(models.MCPService).where(
            models.MCPService.id == service_id
        )
    else:
        service_stmt = select(models.MCPService).where(
            models.MCPService.endpoint == str(endpoint)
        )

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
