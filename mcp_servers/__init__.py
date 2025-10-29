import importlib

from pathlib import Path
from loguru import logger
from fastmcp import FastMCP


def load_mcp_server() -> list[FastMCP]:
    s = []
    for file in Path(__file__).parent.iterdir():
        if file.is_file() and file.stem == "__init__":
            module = importlib.import_module(f"mcp_servers.{file.stem}")
            server = module.get("mcp_server", None)
            if server is None:
                logger.warning("MCP SERVER NOT FOUND, use mcp_server")
            else:
                s.append(server)
    return s
