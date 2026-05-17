from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

__ = load_dotenv(
    dotenv_path=Path("/Users/aayushchaurasia/ZedProjects/Agent2Agent/.env")
)


class UtilityAgent:
    """Utility agent class"""

    def __init__(self) -> None:
        """Constructor for setting up utlity agent components"""
        self._client = MultiServerMCPClient(
            {
                "utility": {
                    "transport": "stdio",
                    "command": "uv",
                    "args": ["run", "./utility_mcp.py"],
                }
            }
        )
        self._agent = None

    @classmethod
    async def create_utility_agent(cls) -> "UtilityAgent":
        """Asynchronously creates and initizalizes the utility agent."""
        instance = cls()
        mcp_tools = await instance._client.get_tools()
        instance._agent = create_agent(
            model="groq:openai/gpt-oss-20b",
            tools=mcp_tools,
            system_prompt="You are a utility agent who has access to utility tools. Use them judiciously.",
        )
        return instance

    async def invoke(self, user_msg):
        """Invokes the agent to process user's query."""
        try:
            if self._agent:
                response = await self._agent.ainvoke({"messages": user_msg})
                return response
        except Exception as e:
            print(f"ERROR: Failed to run utility agent: {e}")
