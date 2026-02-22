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

## Run ADK Web (Local)

Important: run ADK from the `agents/` directory so only agent packages are discovered.

```bash
cd agents
poetry run adk web .
```

Open:
- `http://127.0.0.1:8000/dev-ui/`

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
