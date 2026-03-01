# Farsight AI Clone Design (ADK Implementation Plan)

Last updated: 2026-03-01
Reference company: Farsight AI (finance workflows) at https://www.farsight-ai.com/

## Objective
Build a realistic v1 "Farsight-style" deck workflow in ADK that produces analyst-ready draft slides with citations, starting from a single data source and expanding in phases.

## Product Direction
- Primary value: generate client-ready deck drafts, not generic chat answers.
- Differentiator for v1: speed + source-grounded outputs + fixed template consistency.
- Constraint for v1: single data source to reduce integration risk and ship faster.

## Phases At A Glance
1. Phase 0 - Foundations (1-2 weeks)
- Deck schema, baseline ADK runtime, and observability.

2. Phase 1 - Single-Source MVP (2-3 weeks)
- SEC EDGAR only; generate cited draft decks.

3. Phase 2 - Internal Data Expansion (3-4 weeks)
- Add one internal source (CRM or prior memos) with access controls.

4. Phase 3 - Premium Data + PPT Automation (4-6 weeks)
- Add licensed market data connectors and PowerPoint rendering.

## Phase Plan

### Phase 0: Foundations (1-2 weeks)
1. Define deck schema
- Standard output sections: company overview, business model, financial snapshot, risks, and source appendix.
- Define JSON schema for each section so ADK agents produce structured content.

2. Build base ADK runtime
- Use `LlmAgent` for writing/transforming narrative.
- Use `SequentialAgent` to enforce deterministic step order.
- Use `LoopAgent` only for iterative refinement (max iterations set).
- Add artifact output path for markdown + JSON draft payload.

3. Observability baseline
- Log tool calls and generation stages.
- Store prompt, retrieved records, and output hashes for audit/debug.

### Phase 1: Single-Source Deck Generation (2-3 weeks)
Data source for v1: SEC EDGAR filings only (10-K, 10-Q, 8-K).
Reason: free/public, high-signal financial data, no enterprise contract dependencies.

1. Ingestion
- Build a small ingestion job that fetches filings by ticker/CIK.
- Parse and normalize into one internal format (`filing_chunks`).
- Persist with metadata: `ticker`, `filing_type`, `filing_date`, `section`, `source_url`.

2. Retrieval
- Add one ADK tool: `get_filing_context(ticker, topic)`.
- Retrieve top relevant chunks by section and recency.
- Return citations with each chunk.

3. Deck drafting flow (ADK)
- `Agent A (Planner)`: build section plan from user request.
- `Agent B (Research)`: call `get_filing_context` per section.
- `Agent C (Writer)`: draft section bullets using only retrieved chunks.
- `Agent D (Reviewer)`: check unsupported claims and enforce citation presence.
- `LoopAgent`: rerun Writer + Reviewer until pass or max loops.

4. Outputs
- `deck_draft.md`: sectioned narrative.
- `deck_data.json`: structured fields for future PPT rendering.
- `sources.md`: citation list with filing URLs and dates.

5. Acceptance criteria
- 100% factual bullets must have at least one citation.
- Generation completes in <5 minutes for one company.
- Output format is stable across runs.

### Phase 2: Add Internal Data (3-4 weeks)
1. Add one internal source first (CRM notes or prior internal memos).
2. Merge retrieval ranking: internal context + SEC context.
3. Add style-conditioning pass from prior firm materials.
4. Add role-based access checks on internal documents.

### Phase 3: Premium Data + Presentation Automation (4-6 weeks)
1. Add premium market data connectors (PitchBook / S&P Capital IQ Pro if licensed).
2. Add table/chart generation pipeline for comps and trend visuals.
3. Render to PowerPoint template (placeholder mapping from `deck_data.json`).
4. Introduce human approval gates for valuation and legal-risk slides.

## ADK Architecture (Practical v1)
1. Orchestration
- `SequentialAgent` as top-level controller.
- `LoopAgent` for quality loop on each section.

2. Tools
- `get_filing_context`
- `extract_financial_metrics`
- `save_deck_artifacts`

3. State model
- `session.state.deck_request`
- `session.state.section_plan`
- `session.state.section_drafts`
- `session.state.citations`

4. Artifact model
- Save artifacts per run under a deterministic run id.
- Keep both human-readable (`.md`) and machine-readable (`.json`) outputs.

## Deck Output Strategy (Farsight-Like)
1. Target user outcome
- Deliver actual slide workflow value, not only raw text components.
- Public Farsight positioning indicates end-to-end deliverable automation and PowerPoint editing capability direction.

2. Our phased implementation
- Phase 1: generate deck components (`deck_data.json`, `deck_draft.md`, citations) for fast quality iteration.
- Phase 2/3: produce real `.pptx` files via template mapping and deterministic placement logic.

3. Technical implementation note
- Keep model output schema-first; rendering layer creates slides.
- Avoid direct unconstrained model-to-slide generation.
- Candidate renderer stack: Python `python-pptx` (or equivalent), selected during Phase 3 build.

## Realistic Risks and Controls
1. Risk: Hallucinated metrics
- Control: writer cannot use uncited values; reviewer rejects uncited sentences.

2. Risk: Slow retrieval on long filings
- Control: pre-chunk and cache by filing section/date.

3. Risk: Inconsistent tone/format
- Control: strict output schema + final formatting agent.

4. Risk: Over-scope in early stage
- Control: no paid data connectors in Phase 1; single-source only.

## Near-Term Build Backlog
1. Create `edgar_ingest.py` to normalize filings.
2. Implement ADK tools: context retrieval and metrics extraction.
3. Implement 4-agent deck pipeline with looped review.
4. Add artifact writer and source appendix generator.
5. Add eval set of 10 public companies for regression checks.

## Current Implementation Status (Repo)
1. Completed in code (`agents/farsight_orchestrator`)
- New ADK agent with phase-1 flow:
  - request normalization
  - parallel section research
  - metrics extraction
  - deck JSON draft
  - markdown draft + citation review loop
  - artifact persistence
- Optimization pass: removed separate LLM plan and source-appendix stages to reduce latency and failure surface; sources are now generated deterministically at save time.
- Added ingestion utility script: `agents/farsight_orchestrator/edgar_ingest.py`
  - fetches SEC submissions metadata for selected tickers
  - writes local snapshot JSON for phase-1 ingestion bootstrap
- Artifacts are saved under `agents_workspace/artifacts/farsight/<ticker>/`.

2. Phase-1 realism boundary
- The first implementation uses a curated SEC EDGAR snapshot dataset for deterministic local runs.
- Live SEC ingestion for current filings is available via `edgar_ingest.py`, while section-level parsing/chunking remains curated in this initial cut.

## Sources (Official)
- Main site: https://www.farsight-ai.com/ (checked 2026-03-01)
- Security details: https://www.farsight-ai.com/security (checked 2026-03-01)
- News index: https://www.farsight-ai.com/news (checked 2026-03-01)
- PitchBook integration announcement (2025-09-30): https://www.farsight-ai.com/news/farsight-integrates-with-pitchbook
- Presentable AI acquisition (2025-08-18): https://www.farsight-ai.com/news/farsight-acquires-presentable-ai
- S&P Capital IQ Pro integration (2025-07-01): https://www.farsight-ai.com/blog/farsight-integrates-s-p-capital-iq-pro-data

## Evidence Check Against Actual Farsight AI
1. Clearly supported by official pages
- End-to-end financial workflow automation for decks/CIMs/models/memos.
- Firm-style replication and prior-work matching.
- Integrations with PitchBook and S&P Capital IQ Pro (2025 announcements).
- PowerPoint automation and free-form editing capability direction (Presentable AI acquisition).
- Security/deployment posture: SOC 2 messaging, encrypted data, dedicated VPC options, customer cloud/on-prem options, no training on customer data.

2. Not publicly confirmed in detail
- Exact internal orchestration graph for their production agents.
- Their model-provider mix and routing logic.
- Whether they fine-tune any proprietary or open-weight models for production.

## Model Strategy: What We Can Infer vs What We Cannot
1. Publicly stated facts
- Farsight states that customer data is not used to train models.
- Farsight states LLM interactions run via secure, zero-retention endpoints.

2. Practical inference (medium confidence)
- Their public language is most consistent with a frontier-model endpoint strategy plus strong workflow/context engineering and data integrations.

3. Unknowns (must not assume)
- There is no explicit public statement confirming they do or do not fine-tune models using non-customer datasets.
- Therefore, this design should not depend on any assumption that Farsight's edge comes from fine-tuning.

## Notes
- This plan intentionally starts with one dataset (SEC EDGAR) to stay realistic and shippable.
- Additional data providers should only be added after Phase 1 quality and latency targets are met.
