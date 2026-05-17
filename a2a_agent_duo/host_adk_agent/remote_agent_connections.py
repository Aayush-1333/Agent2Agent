from a2a.client import ClientConfig, create_client
from a2a.types import AgentCard, SendMessageRequest, StreamResponse


class RemoteAgentConnections:
    """A class to hold the connections to remote agents"""

    def __init__(self, agent_card: AgentCard):
        """
        Initializes agent client and card for remote agent

        Args:
            agent_card: Remote agent's card from /.well-known/agent-card.json
        """
        self.agent_client = None
        self.card = agent_card

    async def _async_init_components(self):
        """Asynchronously intialize connections"""
        self.agent_client = await create_client(
            self.card, client_config=ClientConfig(streaming=False)
        )

    @classmethod
    async def _establish_connection(
        cls, agent_card: AgentCard
    ) -> "RemoteAgentConnections":
        """
        Asynchrionously initializes connection with remote agent

        Args:
            agent_card: Remote agent's card

        Returns:
            RemoteAgentConnections instance
        """
        instance = cls(agent_card)
        await instance._async_init_components()
        return instance

    def get_agent(self) -> AgentCard:
        """
        Fetches the remote agent's card

        Returns:
            Agent card object
        """
        return self.card

    async def send_message(self, message_request: SendMessageRequest) -> StreamResponse:
        """
        Sends message to remote agent as role `user` and gets back response asynchrounously.

        Args:
            message_request: The request to be sent to remote agent via A2A

        Returns:
            A streaming response
        """
        if not self.agent_client:
            raise ValueError(f"Agent client not established for {self.card.name}")

        chunks = []
        async for chunk in self.agent_client.send_message(message_request):
            chunks.append(chunk)

        print(f"DEBUG: Got chunks\n\n{chunks}\n***************************")
        if chunks:
            return chunks[-1]
        raise Exception("No response from remote agent.")
