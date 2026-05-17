import asyncio

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette
from utility_agent import UtilityAgent
from utility_agent_executor import UtilityAgentExecutor

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9000


async def initialize_a2a_server():
    agent_skills = [
        AgentSkill(
            id="weather_search",
            name="Search weather",
            description="Helps in getting weather for a city",
            tags=["weather"],
            examples=["Weather in New Delhi"],
        ),
        AgentSkill(
            id="calculate_results",
            name="Result calculator",
            description="Helps in evaluating arithmetic expressions",
            tags=["calculate"],
            examples=["Evaluate: 34 * 22 - 82 / 2", "What is 42 / 2.21 + 73?"],
        ),
    ]

    agent_card = AgentCard(
        name="Utility Agent",
        description="Helps with basic tasks like getting weather and calculations.",
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(),
        supported_interfaces=[
            AgentInterface(url="http://0.0.0.0:9000", protocol_binding="JSONRPC")
        ],
        skills=agent_skills,
    )

    langchain_agent = await UtilityAgent.create_utility_agent()
    agent_executor = UtilityAgentExecutor(langchain_agent)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    app = Starlette(routes=routes)

    return app


if __name__ == "__main__":
    a2a_server = asyncio.run(initialize_a2a_server())
    uvicorn.run(a2a_server, host=DEFAULT_HOST, port=DEFAULT_PORT)
