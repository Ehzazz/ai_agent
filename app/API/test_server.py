# test_server.py
from mcp.server.fastmcp import FastMCP
from typing import Annotated

mcp = FastMCP(name="test", port=8000, cors=True)

@mcp.tool()
def ping(name: Annotated[str, "Your name"]) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    print("Starting test MCP server...")
    mcp.run( transport="http",
    host="0.0.0.0",           # Bind to all interfaces
    port=9000,                # Custom port
    log_level="DEBUG",        # Override global log level)
    )