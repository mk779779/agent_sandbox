# Agent Sandbox

Repository for ADK-based multi-agent experiments and prototypes.

## Repository Layout

- `agents/`: runnable ADK agents
- `models/`: model/design experiments
- `outputs/`: generated artifacts and design notes (git-ignored)
- `pyproject.toml`, `poetry.lock`: shared Python dependencies

Current agent packages in `agents/`:
- `report_gen`: OLAP-style iterative report generation example
- `sec_kpi_orchestrator`: finance KPI investigation workflow with parallel evidence, root-cause analysis, actions, and visualizations
- `farsight_orchestrator`: phase-1 Farsight-style deck drafting workflow using SEC EDGAR context and citation checks

## Prerequisites

- Python 3.10+
- Poetry
- API key(s):
  - `OPENAI_API_KEY` (used by current `openai/...` model config)
  - optional `OPENROUTER_API_KEY`

## Setup

From repo root:

```bash
poetry install
```

Set environment variables (shell or `.env`):

```bash
export OPENAI_API_KEY=your-key
# optional
export OPENROUTER_API_KEY=your-openrouter-key
```

## SQLite for ADK Sessions (Local)

ADK web uses local SQLite sessions by default (`agents/.adk/session.db`).
No database setup is required.

## Run ADK Web (Local)

Important: run ADK from the `agents/` directory so only agent packages are discovered.

```bash
cd agents
poetry run adk web .
```

Open:
- `http://127.0.0.1:8000/dev-ui/`

## Run Session/Event Chat API (`main.py`)

This API supports:
- new session creation when `session_id` is omitted
- existing session continuation when `session_id` is provided
- persistent event logging for user prompts, model responses, and tool calls

Start server from repo root:

```bash
poetry run uvicorn main:app --host 127.0.0.1 --port 8010 --reload
```

Example request (new session):

```bash
curl -sS -X POST http://127.0.0.1:8010/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What time is it in UTC? Use tools if helpful.","user_id":"demo-user","request_id":"req-1"}'
```

Fetch events:

```bash
curl -sS "http://127.0.0.1:8010/sessions/<SESSION_ID>/events"
```

## Docker Deployment

Build from repo root:

```bash
docker build -t sec-kpi-orchestrator:local .
```

Run container:

```bash
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  sec-kpi-orchestrator:local
```

Open:
- `http://127.0.0.1:8000/dev-ui/`

## Outputs and Artifacts

Run outputs are written under `agents/outputs/reports/` (git-ignored), including:
- report markdown
- payload JSON
- trace JSON
- chart files

Top-level `outputs/` is also git-ignored and intended for design/explanation notes.

## Adding a New Agent

1. Create a new subdirectory under `agents/`.
2. Add `agent.py` exporting `root_agent`.
3. Add `__init__.py`.
4. Start ADK web from `agents/` and verify the new agent appears in UI.

## Notes

- If code changes do not appear in ADK web, restart the ADK server.
- `adk web --reload` may not be stable in some environments; manual restart is the reliable path.
