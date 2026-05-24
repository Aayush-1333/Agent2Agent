"""
This file is for managing remote agent connections which are running
as A2A servers (Starlette apps) listening for requests from the host
agent.
"""

import httpx
from a2a.client import Client, ClientConfig, create_client
from a2a.types import AgentCard


class RemoteAgentConnections:
    """A class to hold all remote agent connections"""

    def __init__(self) -> None:
        # 1. Initialize agent and httpx clients
        self._agent_client: Client | None = None  # initially set to `None`
        self._httpx_client = httpx.AsyncClient(timeout=30)

    @classmethod
    async def init_a2a_client(
        cls, agent_card: AgentCard | None
    ) -> "RemoteAgentConnections":
        """Asyncrhonously initializes agent client to call remote agent via A2A"""

        if not agent_card:
            raise ValueError("Invalid agent card!")

        instance = cls()
        # 2. Create a non-streaming agent client based on Agent card
        instance._agent_client = await create_client(
            agent=agent_card,
            client_config=ClientConfig(
                streaming=False, httpx_client=instance._httpx_client
            ),
        )
        return instance

    @property
    def agent_client(self) -> Client:
        """Fetches the client to invoke remote agent"""

        # 3. Return the agent client if configured
        if not self._agent_client:
            raise ValueError("Agent client not initialized or invalid!")
        return self._agent_client
