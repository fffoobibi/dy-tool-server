from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from mcp_server import load_mcp_server

verifier = StaticTokenVerifier(
    tokens={
        "dev-alice-token": {
            "client_id": "alice@company.com",
            "scopes": ["read:data", "write:data", "admin:users"],
        },
        "dev-guest-token": {"client_id": "guest-user", "scopes": ["read:data"]},
    },
    required_scopes=["read:data"],
)


mcp = FastMCP("dy-tool-server MCP Server")
for server in load_mcp_server():
    mcp.mount(server)


def mcp_run(mcp_port: int = 8000):
    """Start Mcp Server"""
    mcp.run(transport="streamable-http", host="localhost", port=mcp_port)


if __name__ == "__main__":
    mcp_run()