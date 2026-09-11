"""LangGraph agent that reasons over the ExpenseTracker MCP server."""

import os
import base64
from datetime import date

from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

# Load a2a_agent/.env regardless of the working directory the server starts in.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

MCP_URL = os.environ.get(
    "MCP_URL", "https://expense-gateway-6i2ud6.5sc6y6-1.usa-e2.cloudhub.io/expensemcp/mcp"
)
MCP_CLIENT_ID = os.environ["MCP_CLIENT_ID"]
MCP_CLIENT_SECRET = os.environ["MCP_CLIENT_SECRET"]

auth = base64.b64encode(
    f"{MCP_CLIENT_ID}:{MCP_CLIENT_SECRET}".encode()
).decode()

SYSTEM_PROMPT = """You are an expense tracking assistant.

You have tools backed by a live expense database:
  - add_expense(date, amount, category, subcategory, note) -> records one expense
  - list_expenses(start_date, end_date) -> raw rows in an inclusive date range
  - summarize(start_date, end_date, category) -> totals grouped by category
  - list_categories() -> categories already present in the database

Rules:
  - Always call a tool for anything involving real expense data. Never invent
    amounts, dates or categories.
  - Dates are ISO strings, YYYY-MM-DD. Today is {today}.
  - Resolve relative dates ("last month", "this week") into concrete ranges
    yourself before calling a tool.
  - Report ONLY what the tool returned. Every amount, category and date in
    your answer must appear verbatim in a tool result.
  - An empty result ([] or no rows) means there is no matching data. Say so
    plainly, e.g. "No expenses are recorded for August 2026." NEVER substitute
    example, typical or plausible figures for missing data, and never pad a
    short result with extra categories.
  - Answer in plain prose with the concrete numbers. Do not mention tool names
    or internal mechanics; the caller may be another agent, not a human.
  - If a request is outside expense tracking, say so briefly.
"""


def _build_llm():
    """Pick the chat model from LLM_PROVIDER (ollama | anthropic | openai | groq)."""
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5"),
            temperature=0,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Put it in a2a_agent/.env "
                "(see .env.example) or export it before starting the server."
            )
        return ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}")


class ExpenseAgent:
    """Wraps a LangGraph ReAct agent; one instance is shared by the A2A server."""

    def __init__(self) -> None:
        self._graph = None
        self._checkpointer = InMemorySaver()

    async def _ensure_graph(self):
        if self._graph is not None:
            return self._graph

        client = MultiServerMCPClient(
            {
                "expense-tracker": {
                    "transport": "streamable_http",
                    "url": MCP_URL,
                    "headers":{
                        "Authorization":f"Basic {auth}"
                    }
                }
            }
        )
        tools = await client.get_tools()
        if not tools:
            raise RuntimeError(f"No tools discovered at {MCP_URL}")

        self._graph = create_react_agent(
            model=_build_llm(),
            tools=tools,
            prompt=SYSTEM_PROMPT.format(today=date.today().isoformat()),
            checkpointer=self._checkpointer,
        )
        return self._graph

    async def tool_names(self) -> list[str]:
        """Used at startup to build the agent card's skills from the live server."""
        client = MultiServerMCPClient(
            {
                "expense-tracker": 
                {
                    "transport": "streamable_http", 
                    "url": MCP_URL,
                    "headers":{
                        "Authorization":f"Basic {auth}"
                    },
                }
            }
        )
        return [t.name for t in await client.get_tools()]

    async def invoke(self, query: str, session_id: str) -> str:
        """Run one turn. `session_id` is the A2A contextId, so a multi-turn
        conversation from a calling agent keeps its history."""
        graph = await self._ensure_graph()
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config={"configurable": {"thread_id": session_id}},
        )
        messages = result.get("messages", [])
        if not messages:
            return "The agent produced no response."

        text = messages[-1].content
        if isinstance(text, list):  # some providers return content blocks
            text = "".join(
                b.get("text", "") for b in text if isinstance(b, dict)
            )
        return (text or "").strip() or "The agent produced an empty response."
