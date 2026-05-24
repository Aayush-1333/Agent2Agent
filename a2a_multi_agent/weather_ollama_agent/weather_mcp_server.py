"""
This is `weather MCP server` created using fastmcp.
It exposes `get_weather` tool to LLM for retrieving weather
details for a given city as input.

The transport of the server is `stdio`.
"""

from fastmcp.server import FastMCP

mcp = FastMCP(name="Weather MCP server")


@mcp.tool()
def get_weather(city: str) -> str:
    return f"Today is cloudy in {city}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
