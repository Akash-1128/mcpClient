# Expense Tracker A2A Agent

Wraps the ExpenseTracker MCP server in a real **A2A agent** so it can be
registered in MuleSoft Agent Fabric via *Register Agent Manually*.

```
Agent Fabric ──A2A / JSON-RPC──> server.py (this agent)
                                     │  LangGraph ReAct loop + OpenAI
                                     └──MCP / streamable-http──> expensetracker-nbel.onrender.com/mcp
```

Fabric does not host agents. That form registers a **pointer** to an agent you
host, so the agent must be reachable at a public URL before registration works.

## Files

| File | Role |
|---|---|
| `agent.py` | LangGraph ReAct agent bound to the 4 MCP tools |
| `executor.py` | Maps A2A task lifecycle onto the agent |
| `server.py` | Agent card + JSON-RPC endpoint |
| `test_client.py` | Calls the agent exactly the way Fabric does |

## Setup

```bash
cp .env.example .env       # then put your OpenAI key in it
../venv/Scripts/python.exe -m pip install -r requirements.txt
```

`.env` is gitignored. `agent.py` loads it by absolute path, so the server picks
it up no matter which directory you start it from.

## Run

```bash
../venv/Scripts/python.exe server.py
```

- Agent card: http://localhost:9000/.well-known/agent-card.json
- A2A endpoint: http://localhost:9000/

Test it:

```bash
../venv/Scripts/python.exe test_client.py "Summarize my spending for September 2026"
```

## Config

| Env var | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` / `anthropic` / `ollama` / `groq` |
| `OPENAI_API_KEY` | — | required when provider is `openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `PUBLIC_URL` | `http://localhost:9000/` | **Must** be the public URL before registering |
| `PORT` | `9000` | |
| `MCP_URL` | the Render MCP endpoint | |

Provider SDKs are imported lazily inside `_build_llm()`, so you only need the
one you actually use installed.

## Making it reachable by Fabric

**Option A — tunnel (fastest for exploring):**

```bash
ngrok http 9000
# restart with the tunnel URL baked into the card:
PUBLIC_URL=https://<id>.ngrok-free.app/ ../venv/Scripts/python.exe server.py
```

**Option B — deploy next to the MCP server** (Render, start command
`python server.py`). Set `OPENAI_API_KEY`, `LLM_PROVIDER=openai` and
`PUBLIC_URL=https://<your-agent>.onrender.com/` as service env vars.

`PUBLIC_URL` matters because Fabric reads the `url` field out of the card and
calls *that*. A card served over ngrok but still saying `localhost` will
register and then fail on every invocation.

## Register in Agent Fabric

1. Start the agent and confirm the card loads at the **public** URL.
2. Generate the card file for the upload field:
   ```bash
   PUBLIC_URL=https://<public-host>/ ../venv/Scripts/python.exe server.py --dump-card
   ```
3. In *Register Agent Manually*:
   - **Name** — `Expense Tracker Agent`
   - **Platform** — pick the custom/other option if present; `MuleSoft` only
     fits if you front the agent with a Mule app
   - **Protocol** — `A2A`
   - **Agent Card File** — upload `agent-card.json`
4. After registering, invoke it from Fabric and watch this server's log — you
   should see `POST /` with `message/send`.

## Note on the MCP server you already registered

Registering the MCP server gave Fabric the four *tools*. This agent is the
*reasoning* layer over them — it turns "how much did I spend last month?" into
the right `summarize` call. Both entries can coexist in Fabric.
