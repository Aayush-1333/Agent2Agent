"""
This is the main agent which will be client-facing for interactions in the UI

Steps taken by host agent:
- Sets remote agent URLs
- Initializes google ADK agent
- Returns the ADK agent instance
"""

import asyncio
import json
import os
import uuid
from pathlib import Path

import httpx
from a2a.client import A2ACardResolver
from a2a.helpers import display_agent_card, get_stream_response_text
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    SendMessageRequest,
    StreamResponse,
    TaskState,
)
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext
from remote_agent_connections import RemoteAgentConnections

__ = load_dotenv(dotenv_path=Path(Path(__file__).parents[2] / ".env"))


class HostAgent:
    def __init__(self) -> None:
        """
        Constructor for Host agent

        Holds the following attributes:
        - remote agent connections
        - agent cards
        - agent infos
        """
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""

    async def _async_init_components(self, remote_agent_addresses: list[str]) -> None:
        """Asynchronous part of initialization"""
        client = httpx.AsyncClient(timeout=30)
        for address in remote_agent_addresses:
            card_resolver = A2ACardResolver(client, address)
            try:
                card = await card_resolver.get_agent_card()  # get agent_card in async

                remote_connection = await RemoteAgentConnections._establish_connection(
                    card
                )
                self.remote_agent_connections[card.name] = remote_connection
                self.cards[card.name] = card
            except httpx.ConnectError as e:
                print(f"ERROR: Failed to get agent card from {address}: {e}")
            except Exception as e:
                print(f"ERROR: Failed to initialize connection for {address}: {e}")

        # Get agent info
        agent_info = []
        for agent_detail_dict in self.list_remote_agents():
            agent_info.append(json.dumps(agent_detail_dict))
        self.agents = "\n".join(agent_info)

    @classmethod
    async def create(cls, remote_agent_addresses: list[str]) -> "HostAgent":
        """Create and asynchronously intialize an instance of HostAgent"""
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance

    async def create_agent(self) -> Agent:
        """Create an instance of the HostAgent"""
        return Agent(
            model=os.getenv("GEMINI_API_KEY", "gemini-3-flash-preview"),
            name="Host_agent",
            instruction=self.root_instruction,
            description="This Host agent orchestrates the decomposition of the user asking questions.",
            tools=[self.send_message],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        """Main instructions for the host agent"""

        return f"""
        **Role:** You are an orcestrator agent whose task is to understand the user's query and
        appropriately delegate tasks to specialized remote agents.

        **Core Directives**

        * **Task Delegation:** Utilize `send_message` tool to delegate task to other available agents.
        * **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions.

        <Available Agents>
        {self.agents}
        </Available Agents>
        """

    def list_remote_agents(self) -> list[dict[str, str]]:
        """List available remote agents you can use to delegate task"""
        if not self.cards:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            print(f"Found agent card: {display_agent_card(card)}")
            print("=" * 100)
            remote_agent_info.append(
                {"name": card.name, "description": card.description}
            )
        return remote_agent_info

    async def send_message(
        self, agent_name: str, task: str, tool_context: ToolContext
    ) -> str | None:
        """Sends a task to remote agent.

        This will send a task to remote agent named agent_name.

        Args:
            agent_name: The name of the agent to send the task to
            task: The comprehensive context summary
            and goal to be achieved regarding user inquiry
            tool_context: The tool context this method runs in

        Yields:
            A dictionary of JSON data
        """
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {agent_name} not found!")

        state = tool_context.state
        state["active_agent"] = agent_name
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f"Client not available for {agent_name}")

        task_id = state.get("task_id")
        context_id = state.get("context_id")

        message_id = ""
        metadata = {}
        if "input_message_metadata" in state:
            metadata.update(**state["input_message_metadata"])
            if "message_id" in state["input_message_metadata"]:
                message_id = state["input_message_metadata"]["message_id"]
        if not message_id:
            message_id = str(uuid.uuid4())

        sender_message = Message(
            message_id=message_id,
            context_id=context_id if context_id else None,
            task_id=task_id if task_id else None,
            role=Role.ROLE_USER,
            parts=[Part(text=task)],
            metadata=metadata,
        )
        message_request = SendMessageRequest(message=sender_message)
        print(f"DEBUG: message_request --> {message_request}", flush=True)
        send_response: StreamResponse = await client.send_message(
            message_request=message_request
        )
        print("send_response:", send_response)

        task_state = send_response.status_update.status.state
        print(f"AAYUSH GOT - {task_state}")
        if task_state == TaskState.TASK_STATE_UNSPECIFIED:
            print("Received non-success response, aborting get task...")
            return None

        # if not isinstance(send_response.task, Task):
        #     print("Received non-task response, aborting get task...")
        #     return None

        return get_stream_response_text(send_response)


def _get_initialized_host_agent_sync() -> Agent:
    """Synchronously creates and initializes Host Agent"""

    async def _async_main() -> Agent:
        host_agent_instance = await HostAgent.create(
            remote_agent_addresses=["http://0.0.0.0:9000"]
        )
        return await host_agent_instance.create_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print(
                f"Warning: Could not initialize RoutingAgent with asyncio.run(): {e}. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing RoutingAgent within an async function in your application."
            )
        raise


root_agent = _get_initialized_host_agent_sync()
