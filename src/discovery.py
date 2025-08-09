from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import Client as FastMCPClient


class DiscoveryClient:
    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger("mcp_storage.discovery")

    def fetch_tools(self, endpoint: str) -> list[dict]:
        """
        Discover tools from a remote MCP service using fastmcp.Client.
        """
        try:
            self.logger.info("Discovering tools", extra={"endpoint": endpoint})
            tools = asyncio.run(_fetch_tools_async(endpoint))
            self.logger.info(
                "Discovery succeeded",
                extra={"endpoint": endpoint, "tools_count": len(tools)},
            )
            return tools
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "Discovery failed", extra={"endpoint": endpoint, "error": str(exc)}
            )
            raise DiscoveryError(f"Failed to fetch tools from {endpoint}: {exc}")


async def _fetch_tools_async(endpoint: str) -> list[dict]:
    tools_out: list[dict] = []
    async with FastMCPClient(endpoint) as client:
        tools: list[Any] = await client.list_tools()
        for item in tools:
            if isinstance(item, dict):
                name = item.get("name")
                description = item.get("description", "") or ""
            else:
                name = getattr(item, "name", None)
                description = getattr(item, "description", "") or ""
            if not name:
                continue
            tools_out.append({"name": name, "description": description})
    return tools_out


class DiscoveryError(RuntimeError):
    pass
