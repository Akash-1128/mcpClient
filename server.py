"""A2A server exposing the ExpenseTracker agent to MuleSoft Agent Fabric."""

import json
import logging
import os

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent import ExpenseAgent
from executor import ExpenseAgentExecutor

logging.basicConfig(level=logging.INFO)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "9000"))
# The URL Agent Fabric will call. Must be the public tunnel/deploy URL, not
# localhost, once you register the agent: it is copied verbatim into the agent
# card, and callers use it as the A2A endpoint.
#   1. PUBLIC_URL          - set explicitly (ngrok, custom domain)
#   2. RENDER_EXTERNAL_URL - injected automatically by Render
#   3. localhost           - local development
PUBLIC_URL = (
    os.environ.get("PUBLIC_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or f"http://localhost:{PORT}"
)
# The card url is the JSON-RPC root, so it must end in a slash.
if not PUBLIC_URL.endswith("/"):
    PUBLIC_URL += "/"

SKILLS = [
    AgentSkill(
        id="add_expense",
        name="Add Expense",
        description=(
            "Record a new expense with a date, amount, category, optional "
            "subcategory and note."
        ),
        tags=["expense", "write", "finance"],
        examples=[
            "Add an expense of 1500 for movie on 2026-07-16 with note 'family outing'",
            "Log 250 rupees spent on groceries today",
        ],
    ),
    AgentSkill(
        id="list_expenses",
        name="List Expenses",
        description="List individual expense entries within an inclusive date range.",
        tags=["expense", "read", "finance"],
        examples=[
            "Show all expenses between 2026-07-01 and 2026-07-31",
            "What did I spend on last week?",
        ],
    ),
    AgentSkill(
        id="summarize_expenses",
        name="Summarize Expenses",
        description=(
            "Summarize spending totals grouped by category over a date range, "
            "optionally filtered to a single category."
        ),
        tags=["expense", "analytics", "finance"],
        examples=[
            "Summarize my spending for July 2026",
            "How much did I spend on travel this quarter?",
        ],
    ),
    AgentSkill(
        id="list_categories",
        name="List Categories",
        description="List every expense category present in the database.",
        tags=["expense", "metadata"],
        examples=["What expense categories exist?"],
    ),
]


def build_agent_card() -> AgentCard:
    return AgentCard(
        protocol_version="0.3.0",
        name="Expense Tracker Agent",
        description=(
            "Tracks and analyses personal expenses. Records new expenses and "
            "answers questions about spending by date range and category, "
            "backed by the ExpenseTracker MCP server."
        ),
        url=PUBLIC_URL,
        version="1.0.0",
        preferred_transport="JSONRPC",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            state_transition_history=False,
        ),
        skills=SKILLS,
    )


def build_app():
    agent = ExpenseAgent()
    handler = DefaultRequestHandler(
        agent_executor=ExpenseAgentExecutor(agent),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=build_agent_card(), http_handler=handler
    ).build()


def dump_card(path: str = "agent-card.json") -> None:
    """Write the card to disk for upload into Agent Fabric's registration form."""
    card = build_agent_card().model_dump(mode="json", exclude_none=True, by_alias=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(card, fh, indent=2)
    print(f"Wrote {path} (url={PUBLIC_URL})")


if __name__ == "__main__":
    import sys

    if "--dump-card" in sys.argv:
        dump_card()
    else:
        print(f"Agent card:  {PUBLIC_URL.rstrip('/')}/.well-known/agent-card.json")
        print(f"A2A JSONRPC: {PUBLIC_URL}")
        uvicorn.run(build_app(), host=HOST, port=PORT)
