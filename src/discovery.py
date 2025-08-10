from __future__ import annotations

import logging

from typing import Any

from fastmcp import Client as FastMCPClient


class DiscoveryClient:
    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger("mcp_storage.discovery")

    async def fetch_tools(self, endpoint: str) -> list[dict]:
        """
        Discover tools from a remote MCP service using fastmcp.Client.
        """
        try:
            self.logger.info("Discovering tools", extra={"endpoint": endpoint})
            tools = await self._fetch_tools_async(endpoint)

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

    async def fetch_description(self, endpoint: str) -> str | None:
        """
        Fetch description from the 'description' MCP resource.

        Returns:
            str | None: The description of the MCP service, or None if not found.
            None is returned if no description resource is found.
            It's not a problem, we will ask a user to provide description
        """
        try:
            self.logger.info("Fetching description", extra={"endpoint": endpoint})
            description = await self._fetch_description_async(endpoint)
            self.logger.info(
                "Description fetched",
                extra={"endpoint": endpoint, "description": description},
            )
            return description
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "Description fetch failed",
                extra={"endpoint": endpoint, "error": str(exc)},
            )
            raise DiscoveryError(f"Failed to fetch description from {endpoint}: {exc}")

    async def _fetch_description_async(self, endpoint: str) -> str | None:
        async with FastMCPClient(endpoint) as client:
            resources = await client.list_resources()
            for resource in resources:
                if resource.name == "description":
                    return await client.read_resource(resource.uri)

        # if no description resource is found, return None
        # It's not a problem, we will ask a user to provide description
        return None

    async def _fetch_tools_async(self, endpoint: str) -> list[dict]:
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


async def main():
    # Introducde for testing purpose
    import os

    client = DiscoveryClient()

    tools = await client.fetch_tools(os.environ.get("MCP_REMOTE_ENDPOINT"))

    print(f"Available tools {tools}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
