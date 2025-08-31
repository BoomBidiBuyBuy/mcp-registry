import os

MCP_PORT = os.getenv("MCP_PORT", 8000)
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")

AGENT_REREAD_HOOK = os.getenv("AGENT_REREAD_HOOK", "")
