# Farsight Orchestrator (Phase 1)

ADK multi-agent workflow for a Farsight-style deck draft using SEC EDGAR context.

## Phase 1 Scope Implemented
- Single data source: curated SEC EDGAR snapshot (`10-K`, `8-K` excerpts)
- Deck flow: request -> section plan -> research -> draft -> critic/refiner loop
- Outputs:
  - `latest_deck_draft.md`
  - `latest_deck_data.json`
  - `latest_sources.md`

Artifacts are saved under:
- `outputs/farsight/<ticker>/`

## Agent Flow
1. `request_agent` (normalize ticker/deck type/audience)
2. `research_parallel_agent` (overview/business model/financial/risk/catalyst context)
3. `metrics_agent` (financial snapshot metrics)
4. `deck_payload_agent` (structured deck JSON)
5. `writer_agent` (markdown draft)
6. `refinement_loop_agent` (`critic_agent` + `refiner_agent`)

Source appendix is generated deterministically during artifact save (not as a separate LLM stage).

## Run
From repository root:

```bash
cd agents
poetry run adk web .
```

In ADK web, choose `farsight_orchestrator` and prompt:
- `Build an investment snapshot deck for NVDA for internal IC.`
- `Create a risk brief for MSFT.`

## OpenTelemetry (Tracing + Metrics)

Enable OTel for farsight with:

```bash
export FARSIGHT_OTEL_ENABLED=true
export OTEL_SERVICE_NAME=farsight-orchestrator
# Optional OTLP backend; if unset, telemetry prints to console.
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
export OTEL_EXPORTER_OTLP_INSECURE=true
```

Emitted spans/metrics include:
- `tool.*` spans for SEC tools and artifact saves
- `workflow.save_outputs`, `workflow.exit_loop`, `workflow.after_loop`
- `farsight_tool_calls_total`, `farsight_tool_errors_total`, `farsight_tool_latency_ms`, `farsight_artifact_saves_total`

## Notes
- SEC tools are live-first:
  - attempt live SEC APIs (`submissions`, `companyfacts`) for fresh filings/metrics
  - automatically fall back to curated local snapshot data if SEC/network is unavailable
- For production use, set a valid contact in `SEC_USER_AGENT`.
