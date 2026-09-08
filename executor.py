"""Bridges the A2A protocol onto the LangGraph ExpenseAgent."""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TextPart, UnsupportedOperationError
from a2a.utils import new_task
from a2a.utils.errors import ServerError

from agent import ExpenseAgent

logger = logging.getLogger(__name__)


class ExpenseAgentExecutor(AgentExecutor):
    def __init__(self, agent: ExpenseAgent) -> None:
        self.agent = agent

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        query = context.get_user_input()

        task = context.current_task
        if task is None:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()

        try:
            answer = await self.agent.invoke(query, task.context_id)
        except Exception as exc:  # surface failures as A2A task failures
            logger.exception("Expense agent failed")
            await updater.failed(
                updater.new_agent_message(
                    [Part(root=TextPart(text=f"Expense agent error: {exc}"))]
                )
            )
            return

        await updater.add_artifact(
            [Part(root=TextPart(text=answer))],
            name="expense_result",
        )
        await updater.complete()

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())
