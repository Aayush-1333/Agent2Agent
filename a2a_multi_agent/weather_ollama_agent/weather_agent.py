from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_toolsets


class WeatherAgent:
    """Weather agent to fetch weather conditions for any city"""

    def __init__(self) -> None:
        self._toolsets = load_mcp_toolsets("./mcp_config.json")
        self._agent = Agent(
            model="ollama:granite4:3b",
            name="Weather Agent",
            description="Fetches the weather details of any city using specialized tools.",
            instructions="You are a weather agent who can fetch weather details for any city asked by the user.",
            toolsets=self._toolsets,
        )

    async def invoke(self, user_msg: str):
        result = await self._agent.run(user_prompt=user_msg)
        return result.output
