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

## Notes
- This implementation is deterministic/local for development and does not call SEC APIs live yet.
- Live ingestion can replace the curated dataset without changing the orchestration contract.
