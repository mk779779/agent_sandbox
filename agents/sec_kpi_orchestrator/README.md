# SEC KPI Orchestrator

ADK multi-agent workflow for finance KPI monitoring and diagnosis using deterministic SEC-style tools.

## Architecture

Flow:
1. `request_agent` normalizes user ask into a strict request contract
2. `plan_agent` builds an explicit analysis plan
3. `query_parallel_agent` runs baseline, variance, and peer queries in parallel
4. `anomaly_agent` flags KPI outliers
5. `root_cause_agent` ranks segment drivers
6. `action_agent` maps drivers to playbooks
7. `writer_agent` drafts report
8. `refinement_loop_agent` critic/refiner loop enforces output quality

## Files

- `agent.py`: ADK entry point (`root_agent`)
- `loop_agent.py`: orchestration graph and loop callbacks
- `finance_tools.py`: deterministic finance query tools and playbooks

## Output Artifacts

- `agents/outputs/reports/latest_sec_kpi_report.md`
- `agents/outputs/reports/latest_sec_kpi_payload.json`

## Run

```bash
poetry run adk web --reload --reload_agents .
```

Then select `sec_kpi_orchestrator` in ADK web.
