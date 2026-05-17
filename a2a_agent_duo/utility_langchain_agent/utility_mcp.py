import logging

from fastmcp import FastMCP

logger = logging.getLogger("uvicorn.agent")

mcp = FastMCP(name="utility MCP server")


@mcp.tool()
def get_weather(city: str) -> str:
    """
    Gets weather info for a city

    Args:
        city: Name of the city
    Returns:
        Returns the weather info in string.
    """
    logger.info("Invoked get_weather tool...")
    return f"It's cloudy in {city}"


@mcp.tool()
def calculate(expr: str) -> str:
    """
    Calculates arithmetic expressions using eval

    Args:
        expr: Arithmetic expression to evaluate
    Returns:
        Final result after calculation in string.
    """
    logger.info("Invoked calculate tool...")
    return str(eval(expr))


if __name__ == "__main__":
    logger.info("Starting utility MCP server for remote agent...")
    mcp.run(transport="stdio")
