import logging

from a2a.helpers import get_message_text
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Task, TaskState
from utility_agent import UtilityAgent

logger = logging.getLogger("uvicorn.agent")


class UtilityAgentExecutor(AgentExecutor):
    """Utility agent executor to handle requests via A2A"""

    def __init__(self, agent: UtilityAgent) -> None:
        self._agent = agent

    async def _process_request(
        self, message: Message, task_updater: TaskUpdater
    ) -> None:
        try:
            result = await self._agent.invoke(get_message_text(message))
            logger.info(f"DEBUG: Got result: {result}")
            if result:
                await task_updater.update_status(TaskState.TASK_STATE_COMPLETED)

        except Exception as e:
            print(f"ERROR: Failed to process request: {e}")

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        print(f"DEBUG: [UtilityAgentExecutor] execute entered", flush=True)
        try:
            print(
                f"DEBUG: [UtilityAgentExecutor] execute - task_id = {context.task_id}, context_id = {context.context_id}",
                flush=True,
            )
            print(
                f"DEBUG: [UtilityAgentExecutor] execute - context.current_task = {context.current_task}",
                flush=True,
            )

            # Run the agent until either complete or the task is suspended.
            updater = TaskUpdater(event_queue, context.task_id, context.context_id)

            # Immediately notify that the task is submitted.
            if not context.current_task:
                print(
                    f"DEBUG: [UtilityAgentExecutor] No current_task, enqueuing Task and sending TASK_STATE_SUBMITTED for task_id = {context.task_id}",
                    flush=True,
                )
                # Enqueue the task first as required by A2A
                await event_queue.enqueue_event(
                    Task(
                        id=context.task_id,
                        context_id=context.context_id,
                    )
                )
                await updater.update_status(TaskState.TASK_STATE_SUBMITTED)
            else:
                print(
                    f"DEBUG: [UtilityAgentExecutor] current_task exists for task_id = {context.task_id}, state = {context.current_task.status.state}",
                    flush=True,
                )

            await updater.update_status(TaskState.TASK_STATE_WORKING)
            await self._process_request(context.message, updater)
        except Exception as e:
            print(f"ERROR: Failed to start agent executor: {e}")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise RuntimeError("Cancel task not supported!")
