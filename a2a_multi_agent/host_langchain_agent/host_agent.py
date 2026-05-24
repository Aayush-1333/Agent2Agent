import asyncio
import json
import uuid
from pathlib import Path

import httpx
from a2a.client import A2ACardResolver
from a2a.helpers import get_stream_response_text, new_text_message
from a2a.types import AgentCard, Role, SendMessageRequest, StreamResponse, TaskState
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import (
    StructuredTool,  # Direct construction avoids @tool signature bugs
)
from langgraph.graph.state import CompiledStateGraph
from remote_agent_connections import RemoteAgentConnections

__ = load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env")


class HostAgent:
    def __init__(self) -> None:
        """Constructor for Host agent"""

        # 1. Initialize httpx client, mapping of remote agent connections,
        # Agent cards followed by agent clients info as string
        self.httpx_client = httpx.AsyncClient(timeout=30)
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""

    async def async_init_components(self, remote_agent_connections: list[str]) -> None:
        """
        Asynchronously initialize remote agent connections, agent informations and agent cards

        Args:
            remote_agent_connections: List of remote agent URLs
        """

        # 2.1 Iterate over agent URLs to populate remote agent connections and agent cards attributes
        for address in remote_agent_connections:
            try:
                card_resolver = A2ACardResolver(self.httpx_client, address)
                card = await card_resolver.get_agent_card()
                remote_connection = await RemoteAgentConnections.init_a2a_client(card)
                self.remote_agent_connections[card.name] = remote_connection
                self.cards[card.name] = card
            except httpx.ConnectError as e:
                print(f"ERROR: Failed to get agent card from {address}: {e}")
            except Exception as e:
                print(f"Failed to initialize connection for {address}: {e}")

        # 2.2 Fetch agent names and descriptions
        agents_info = []
        for agent_detail_dict in self.list_remote_agents():
            agents_info.append(json.dumps(agent_detail_dict))
        self.agents = "\n".join(agents_info)

    def list_remote_agents(self) -> list[dict[str, str]]:
        """Returns remote agents information via agent cards"""

        if not self.cards:
            return []

        remote_agents_info = []
        for card in self.cards.values():
            print(f"Found agent card: {card.name}")
            remote_agents_info.append(
                {"name": card.name, "description": card.description}
            )
        return remote_agents_info

    @classmethod
    async def create(cls, remote_agents_list: list[str]) -> "HostAgent":
        """Create and asynchronously initializes the components"""

        instance = cls()
        await instance.async_init_components(remote_agents_list)
        return instance

    def create_host_agent(self):
        # FIX 1: Instead of using @tool on a class instance method, build a
        # StructuredTool explicitly. This strips 'self' from the LLM parameter signature.
        #
        # FIX 2: Since your Gradio script calls host_agent.invoke() synchronously,
        # we provide a clean synchronous function wrapper that safely bridges the
        # async A2A communication over an independent running event loop.

        def sync_tool_bridge(agent_name: str, task: str) -> str:
            """Synchronous adapter boundary for the async agent task network call."""
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # If an event loop is already occupied on this thread, spawn a task safely
                import nest_asyncio

                nest_asyncio.apply()
                return loop.run_until_complete(
                    self._execute_send_message(agent_name, task)
                )
            else:
                return loop.run_until_complete(
                    self._execute_send_message(agent_name, task)
                )

        a2a_tool = StructuredTool.from_function(
            func=sync_tool_bridge,
            name="send_req_message",
            description="Sends a task to specified agent by its name. Requires 'agent_name' and a clear summary string for 'task'.",
        )

        return create_agent(
            model="groq:openai/gpt-oss-20b",
            tools=[a2a_tool],
            system_prompt=f"""
            **Role:** You are an orchestrator agent whose task is to understand the user's query and
            appropriately delegate tasks to specialized remote agents.

            **Core Directives**

            * **Task Delegation:** Utilize `send_req_message` tool to delegate task to other available agents.
            * **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions.

            <Available Agents>
            {self.agents}
            </Available Agents>
            """,
        )

    async def _execute_send_message(self, agent_name: str, task: str) -> str:
        """
        Isolated underlying asynchronous worker to execute the real A2A stream payload.
        """
        # 4.1 check whether the remote agent name exists in list or not
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent name: {agent_name} not found!!")

        # 4.2 Fetch remote agent client by its name
        a2a_client = self.remote_agent_connections.get(agent_name, None)
        if not a2a_client:
            raise ValueError(f"Client not available for: {agent_name}")

        # 4.3 Create a request
        execution_id = str(uuid.uuid4())
        req_msg = SendMessageRequest(
            message=new_text_message(
                text=task,
                task_id=execution_id,
                context_id=execution_id,
                role=Role.ROLE_USER,
            )
        )

        # 4.4 Send request to remote agent
        response_chunks: list[StreamResponse] = []
        async for chunks in a2a_client.agent_client.send_message(request=req_msg):
            response_chunks.append(chunks)

        if not response_chunks:
            return "Task failed: Received an empty network response stream from remote agent."

        # 4.5 Receive the response
        final_response = response_chunks[-1]
        task_state = final_response.status_update.status.state
        if task_state == TaskState.TASK_STATE_COMPLETED:
            return get_stream_response_text(final_response)

        return "Task execution failed on remote destination node."


def get_initialized_host_sync() -> CompiledStateGraph:
    async def async_main() -> CompiledStateGraph:
        host_agent_instance = await HostAgent.create(["http://localhost:9900"])
        return host_agent_instance.create_host_agent()

    try:
        host_agent = asyncio.run(async_main())
        return host_agent
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print(
                f"Warning: Could not initialize RoutingAgent with asyncio.run(): {e}. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing RoutingAgent within an async function in your application."
            )
        raise


root_agent = get_initialized_host_sync()
