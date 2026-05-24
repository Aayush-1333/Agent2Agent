"""
This is the main file for weather ollama agent which will be wrapped
as an A2A server to handle incoming requests from the client A2A agent.

The server is passing its routes which will be handled by
the Starlette application.
"""

import asyncio
from pathlib import Path

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from dotenv import load_dotenv
from starlette.applications import Starlette
from weather_agent_executor import WeatherAgentExecutor

__ = load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env")


async def initiaize_a2a_server():
    # 1. Create Agent skill
    agent_skill = AgentSkill(
        id="get_weather",
        name="get weather",
        description="Fetches weather for a city.",
        tags=["weather"],
        examples=[
            "How's the weather in New York City?",
            "What's the weather in Mumbai today?",
        ],
    )

    # 2. Create Agent card
    agent_card = AgentCard(
        name="Weather agent",
        description="Fetches weather conditions for a city.",
        supported_interfaces=[
            AgentInterface(url="http://localhost:9900", protocol_binding="JSONRPC")
        ],
        skills=[agent_skill],
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
    )

    # 3. Initialize Agent executor
    weather_agent_executor = WeatherAgentExecutor()

    # 4. Create default request handler to pass reuqests to agent_executor
    request_handler = DefaultRequestHandler(
        agent_executor=weather_agent_executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    # 5. Pass the routes to Starlette app
    app = Starlette(routes=routes)
    return app


if __name__ == "__main__":
    a2a_server = asyncio.run(initiaize_a2a_server())

    # 6. Start the Starlette app as A2A server on port 9000
    uvicorn.run(a2a_server, host="0.0.0.0", port=9900)
