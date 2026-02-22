# SEC KPI Orchestrator - Explanation

## Purpose
`sec_kpi_orchestrator` is a multi-agent ADK system that turns a finance investigation request into:
- a human-readable KPI report
- a machine-readable action payload
- chart visualizations
- a run trace for debugging

It uses deterministic tools for KPI math and LLM agents for orchestration and narrative.

## Source Layout
Core source files:
- `agent.py`: exports `root_agent`
- `loop_agent.py`: ADK orchestration and callbacks
- `finance_tools.py`: deterministic KPI, variance, peer, anomaly, root-cause, playbook, and visualization tools

Runtime/generated artifacts:
- `__pycache__/`
- `.adk/session.db`

Output artifacts:
- `agents/outputs/reports/latest_sec_kpi_report.md`
- `agents/outputs/reports/latest_sec_kpi_payload.json`
- `agents/outputs/reports/latest_sec_kpi_trace.json`
- `agents/outputs/reports/charts/kpi_qoq_delta.svg`
- `agents/outputs/reports/charts/segment_qoq_delta.svg`

## End-to-End Flow
1. Request normalization
- `request_agent` resolves ticker, period, metrics, compare modes.

2. Plan generation
- `plan_agent` creates an explicit analysis plan.

3. Parallel evidence fan-out
- baseline KPI query
- QoQ variance query
- peer benchmark query

4. Diagnosis and actions
- anomaly detection
- root-cause ranking by segment
- deterministic playbook generation

5. Visualization
- `visualization_agent` calls deterministic chart tool
- generates KPI QoQ delta chart and segment driver delta chart
- saves local SVGs and publishes ADK artifacts (when available)

6. Narrative + quality gate
- writer produces report with required sections
- critic verifies structure, evidence, and action coverage
- refiner iterates until completion criteria pass

7. Persistence
- report, payload, and trace are saved to disk

## Context Engineering In Use
1. Structured state handoffs
- dedicated keys per stage (`request_contract`, `variance_result`, `action_result`, `visualization_result`, etc.)

2. Scoped context windows
- internal agents mostly run with `include_contents="none"`

3. Evidence-first output
- expected query ID references in narrative

4. Critic/refiner loop
- prevents single-pass low-quality output

5. Trace capture
- final state snapshot saved as `latest_sec_kpi_trace.json`

6. Artifact-aware visualization
- charts are saved as ADK artifacts via `ToolContext.save_artifact(...)`

## Test Prompts
1. Baseline full run
`Analyze MSFT for 2025Q4. Focus on revenue, gross_margin_pct, operating_margin_pct, fcf, net_debt. Compare QoQ and peer, then give root causes and actions.`

2. Hardware company comparison
`Run KPI investigation for AAPL 2025Q4 with revenue, operating_margin_pct, fcf, and net_debt. Compare QoQ and peer, then provide action recommendations.`

3. Internet company anomaly focus
`Analyze GOOGL in 2025Q4. Highlight anomaly candidates first, then explain segment-level root causes and recommended actions.`

4. Visualization-heavy run
`Analyze MSFT 2025Q4 and include visualization details for KPI QoQ deltas and segment driver deltas in the report.`

## Run Locally
```bash
cd /Users/masaCoding/codingmain/agent_sandbox/agents
poetry run adk web .
```

Open:
- `http://127.0.0.1:8000/dev-ui/`

## Docker Deployment
From repo root (`/Users/masaCoding/codingmain/agent_sandbox`):

```bash
docker build -t sec-kpi-orchestrator:local .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  sec-kpi-orchestrator:local
```

Open:
- `http://127.0.0.1:8000/dev-ui/`

## Quick Validation Checklist
After each run:
1. `latest_sec_kpi_payload.json` is valid JSON.
2. `latest_sec_kpi_report.md` contains all actions from payload.
3. `latest_sec_kpi_trace.json` contains expected stage keys.
4. Evidence query IDs in report exist in trace outputs.
5. `charts/kpi_qoq_delta.svg` and `charts/segment_qoq_delta.svg` are generated.
