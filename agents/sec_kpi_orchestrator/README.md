# SEC KPI Orchestrator

ADK multi-agent workflow for finance KPI investigation using deterministic tools plus an LLM writer/critic loop.

## Current Structure

Required files:
- `agent.py`: ADK entry point (`root_agent`)
- `loop_agent.py`: orchestration graph (`SequentialAgent`, `ParallelAgent`, `LoopAgent`)
- `finance_tools.py`: deterministic KPI, variance, peer, anomaly, root-cause, and playbook tools

Optional/generated at runtime (not part of source design):
- `__pycache__/`
- `.adk/session.db`

## Agent Flow
1. `request_agent`
2. `plan_agent`
3. `query_parallel_agent` (`baseline`, `variance`, `peer` in parallel)
4. `anomaly_agent`
5. `root_cause_agent`
6. `action_agent`
7. `visualization_agent` (creates chart SVGs and publishes ADK artifacts)
8. `writer_agent`
9. `refinement_loop_agent` (`critic_agent` + `refiner_agent`)

## Output Artifacts
Written to `agents/outputs/reports/`:
- `latest_sec_kpi_report.md`
- `latest_sec_kpi_payload.json`
- `latest_sec_kpi_trace.json`
- `charts/kpi_qoq_delta.svg`
- `charts/segment_qoq_delta.svg`

## Visualizations
The visualization stage builds two deterministic charts:
1. KPI QoQ delta (%) bar chart
2. Segment QoQ delta (%) bar chart

They are saved locally and also published as ADK artifacts (when artifact service is available), so they can be surfaced in ADK web conversations.

## Run
Always run ADK from `agents/` so only agent packages are discovered.

```bash
cd /Users/masaCoding/codingmain/agent_sandbox/agents
poetry run adk web .
```

UI:
- `http://127.0.0.1:8000/dev-ui/`

## OpenTelemetry (Tracing + Metrics)

`sec_kpi_orchestrator` includes OTel instrumentation for:
- tool-call spans and latency/error metrics
- workflow save/exit callbacks and artifact-save counters

Enable with env vars before running ADK:

```bash
export SEC_KPI_OTEL_ENABLED=true
export OTEL_SERVICE_NAME=sec-kpi-orchestrator
# Optional: send to an OTLP collector. If omitted, telemetry prints to console.
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
export OTEL_EXPORTER_OTLP_INSECURE=true
```

## Docker Deployment
Build from repo root (`agent_sandbox`):

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

Notes:
- Container command runs: `adk web --host 0.0.0.0 --port 8000 /app/agents`
- If you want persisted runtime artifacts, mount a volume for `/app/agents/.adk` and `/app/agents/outputs`.

## Reviewed Optimizations
Already addressed:
- Laggard selection only includes negative QoQ drivers.
- Payload is persisted as strict JSON.
- Report save strips markdown fences.
- Trace snapshot is persisted for flow debugging.
- Writer/critic enforce action coverage from payload.

Still recommended:
1. Remove duplicate variance computation in anomaly stage.
- `anomaly_agent` currently recomputes variance via tool call; it should consume `variance_result` directly.

2. Replace stringified JSON state with typed contracts.
- Current state stores many tool outputs as strings; typed JSON objects would reduce parsing errors.

3. Add claim-evidence validator before critic pass.
- Enforce numeric claim mapping to `(query_id, field)`.

4. Minimize optional stage noise.
- `plan_agent` can become optional if not needed for downstream behavior.
