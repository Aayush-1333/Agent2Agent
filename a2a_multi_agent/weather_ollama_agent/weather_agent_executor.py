from a2a.helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from weather_agent import WeatherAgent


class WeatherAgentExecutor(AgentExecutor):
    """Weather agent executor to wrap pydantic AI agent"""

    def __init__(self) -> None:
        self._weather_agent = WeatherAgent()

    async def _process_request(
        self, context: RequestContext, task_updater: TaskUpdater
    ):
        # 4. Invoke the weather agent and marks the task `complete` on getting result
        result = await self._weather_agent.invoke(context.get_user_input())
        if result:
            await task_updater.complete(
                new_text_message(
                    text=result, context_id=context.context_id, task_id=context.task_id
                )
            )
        else:
            await task_updater.failed(
                new_text_message(
                    text="Task failed to process!",
                    context_id=context.context_id,
                    task_id=context.task_id,
                )
            )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # 1. Get incoming message (context) from host agent and enqueue it in event queue
        req_message = context.message
        req_task_id = context.task_id
        req_context_id = context.context_id
        if req_message and req_task_id and req_context_id:
            await event_queue.enqueue_event(req_message)

            # 2. Initialize task updater and send task update status to `submitted`
            updater = TaskUpdater(
                event_queue=event_queue, task_id=req_task_id, context_id=req_context_id
            )
            await updater.submit(
                new_text_message(
                    text="Task submitted to weather agent.",
                    context_id=req_context_id,
                    task_id=req_task_id,
                )
            )

            # 3. Marks the task as `working` and call process request
            await updater.start_work(
                new_text_message(
                    text="Task in progress.",
                    context_id=req_context_id,
                    task_id=req_task_id,
                )
            )
            await self._process_request(context, updater)
        else:
            raise ValueError("Task has either unknown message, task id or context id!")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Raise exception as cancel task is not supported
        raise RuntimeError("Cancel task not supported!!")
