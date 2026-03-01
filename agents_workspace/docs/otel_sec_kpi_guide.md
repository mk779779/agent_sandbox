# OTel Guide for `sec_kpi_orchestrator`

## What this feature does
The `sec_kpi_orchestrator` has OpenTelemetry (OTel) instrumentation for tracing and metrics.

Instrumentation is implemented in:
- `agents/sec_kpi_orchestrator/observability.py`
- decorators applied in `agents/sec_kpi_orchestrator/finance_tools.py`
- workflow spans in `agents/sec_kpi_orchestrator/loop_agent.py`

When enabled, it records:
1. Tool spans (each tool call)
2. Workflow spans (`save_outputs`, `exit_loop`, `after_loop`)
3. Tool metrics (count/errors/latency)
4. Artifact save counters

## How it is enabled
OTel is off by default.

Enable with env vars:
```bash
export SEC_KPI_OTEL_ENABLED=true
export OTEL_SERVICE_NAME=sec-kpi-orchestrator
```

Optional OTLP export target:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
export OTEL_EXPORTER_OTLP_INSECURE=true
```

If `OTEL_EXPORTER_OTLP_ENDPOINT` is not set, spans and metrics are exported to console.

## What gets emitted

### Span names
- `tool.build_investigation_request`
- `tool.build_finance_analysis_plan`
- `tool.execute_kpi_baseline_query`
- `tool.execute_kpi_variance_query`
- `tool.execute_kpi_peer_query`
- `tool.detect_kpi_anomalies`
- `tool.rank_root_causes`
- `tool.map_causes_to_playbooks`
- `tool.generate_kpi_visualizations`
- `workflow.save_outputs`
- `workflow.exit_loop`
- `workflow.after_loop`

Common span attributes:
- `tool.name`
- `ticker`
- `period`
- `error.type` (on errors)

### Metric names
- `sec_kpi_tool_calls_total` (counter)
- `sec_kpi_tool_errors_total` (counter)
- `sec_kpi_tool_latency_ms` (histogram)
- `sec_kpi_artifact_saves_total` (counter)

Common metric attributes:
- `tool.name`
- `tool.status`
- `artifact.kind`
- `artifact.status`

## How to run and view telemetry

### A) Console mode (quickest)
1. Start ADK web with OTel enabled:
```bash
cd /Users/masaCoding/codingmain/agent_sandbox/agents
SEC_KPI_OTEL_ENABLED=true OTEL_SERVICE_NAME=sec-kpi-orchestrator poetry run adk web .
```
2. Run a sec_kpi prompt in ADK UI.
3. Check terminal output for JSON-formatted spans and metrics.

### B) OTLP mode (collector/backend)
1. Start local OTel + Grafana stack:
```bash
cd /Users/masaCoding/codingmain/agent_sandbox/scripts/observability
./run_otel_stack.sh up ui
```
2. Run ADK web with endpoint configured:
```bash
cd /Users/masaCoding/codingmain/agent_sandbox/agents
SEC_KPI_OTEL_ENABLED=true \
OTEL_SERVICE_NAME=sec-kpi-orchestrator \
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 \
OTEL_EXPORTER_OTLP_INSECURE=true \
poetry run adk web .
```
3. Open Grafana: `http://127.0.0.1:3000` (login `admin/admin`).
4. In Grafana, use:
- Explore -> data source `Tempo` -> query service `sec-kpi-orchestrator` for traces.
- For Prometheus metrics, start full mode first: `./run_otel_stack.sh up full`.
5. Inspect:
- trace timeline by span name
- histogram `sec_kpi_tool_latency_ms`
- error counter `sec_kpi_tool_errors_total`

## Where telemetry is saved
With the local stack, telemetry is persisted in Docker volumes:
- `scripts/observability` stack:
  - `tempo_data` (traces)
  - `prometheus_data` (metrics, only in `full` mode)
  - `grafana_data` (Grafana state/dashboards)

You can stop/start without losing data:
```bash
cd /Users/masaCoding/codingmain/agent_sandbox/scripts/observability
./run_otel_stack.sh down ui
./run_otel_stack.sh up ui
```

## How to tell it is working
You should see at least one of these after running a prompt:
- Span entries named `tool.*` and `workflow.*`
- Metrics with `sec_kpi_*` names

If you only see normal app logs and no telemetry:
- confirm `SEC_KPI_OTEL_ENABLED=true`
- confirm the prompt actually used `sec_kpi_orchestrator`
- if using OTLP, verify collector endpoint/port is reachable

## Current scope and limits
Current instrumentation covers sec_kpi tool/workflow boundaries.
It does not yet include:
- per-request/session correlation IDs on all spans
- LLM token usage metrics
- full ADK event-to-span linking across every agent node
