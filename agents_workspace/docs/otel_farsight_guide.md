# OTel for Farsight Orchestrator

## Enable and run
```bash
cd /Users/masaCoding/codingmain/agent_sandbox/agents
FARSIGHT_OTEL_ENABLED=true \
OTEL_SERVICE_NAME=farsight-orchestrator \
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 \
OTEL_EXPORTER_OTLP_INSECURE=true \
poetry run adk web .
```

If you want console output only (no backend), omit `OTEL_EXPORTER_OTLP_ENDPOINT`.

## What is instrumented
- Tool spans (`tool.*`) on:
  - `build_deck_request`
  - `get_filing_context`
  - `extract_financial_metrics`
  - `build_sources_markdown`
  - `save_deck_artifacts`
- Workflow spans:
  - `workflow.save_outputs`
  - `workflow.exit_loop`
  - `workflow.after_loop`

## Metrics emitted
- `farsight_tool_calls_total`
- `farsight_tool_errors_total`
- `farsight_tool_latency_ms`
- `farsight_artifact_saves_total`

## View in Grafana
1. Start stack:
```bash
cd /Users/masaCoding/codingmain/agent_sandbox/scripts/observability
./run_otel_stack.sh
```
2. Open Grafana: `http://127.0.0.1:3000` (`admin/admin`)
3. In Explore:
- Data source `Tempo`: filter service `farsight-orchestrator` to inspect traces.
- Data source `Prometheus`: query `farsight_tool_calls_total`, `farsight_tool_latency_ms`.

## Persistence
With the local stack, data is persisted in Docker volumes:
- `tempo_data` (traces)
- `prometheus_data` (metrics)
- `grafana_data` (Grafana state)
