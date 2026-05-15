import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from agent_executor import GreetingAgentExecutor
from starlette.applications import Starlette

if __name__ == "__main__":
    skill = AgentSkill(
        id="hello world",
        name="Greet",
        description="Return a greeting",
        tags=["hello", "world", "greeting"],
        examples=["Hey", "Hello", "Hi"],
    )

    agent_card = AgentCard(
        name="Greeting Agent",
        description="A simple agent that returns a greeting",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[skill],
        version="1.0.0",
        capabilities=AgentCapabilities(),
        supported_interfaces=[
            AgentInterface(protocol_binding="JSONRPC", url="http://0.0.0.0:9999")
        ],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=GreetingAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    app = Starlette(routes=routes)

    uvicorn.run(app, host="0.0.0.0", port=9999)
