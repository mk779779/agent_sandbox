# Farsight Session I/O Walkthrough

## Scope
- Session ID: `eb803ada-0600-4ba4-96d1-f43cb3779814`
- Agent: `farsight_orchestrator`
- User prompt: `make deck for nvda`

## User input
- `make deck for nvda`

## Call-by-call input/output snippets

### 1) `request_agent` -> `build_deck_request`
Input snippet:
```json
null
```
Output snippet:
```json
{
  "deck_request": {
    "ticker": "NVDA",
    "deck_type": "investment_snapshot",
    "audience": "internal_ic",
    "allowed_topics": [
      "business_model",
      "catalysts",
      "financial_snapshot",
      "overview",
      "risks"
    ]
  }
}
```
What this means:
- The free-text prompt was normalized into a strict deck request contract.

### 2) Parallel research calls -> `get_filing_context`
Called by 5 agents with these inputs:

Input (`overview_research_agent`):
```json
{"ticker": "NVDA", "topic": "overview"}
```
Output snippet:
```json
{
  "ticker": "NVDA",
  "topic": "overview",
  "context_chunks": [
    {
      "citation_id": "NVDA-10K-20260225-1",
      "excerpt": "Recent 10-K filed on 2026-02-25; use this filing as primary company disclosure context."
    }
  ]
}
```

Input (`business_model_research_agent`):
```json
{"ticker": "NVDA", "topic": "business_model"}
```
Output snippet:
```json
{
  "ticker": "NVDA",
  "topic": "business_model",
  "context_chunks": [
    {
      "citation_id": "NVDA-10K-20260225-1",
      "excerpt": "Review business section and MD&A for operating model updates."
    }
  ]
}
```

Input (`financial_research_agent`):
```json
{"ticker": "NVDA", "topic": "financial_snapshot"}
```
Output snippet:
```json
{
  "ticker": "NVDA",
  "topic": "financial_snapshot",
  "context_chunks": [
    {
      "citation_id": "NVDA-10K-20260225-1",
      "excerpt": "Use reported statements and MD&A for latest financial profile."
    }
  ]
}
```

Input (`risk_research_agent`):
```json
{"ticker": "NVDA", "topic": "risks"}
```
Output snippet:
```json
{
  "ticker": "NVDA",
  "topic": "risks",
  "context_chunks": [
    {
      "citation_id": "NVDA-10K-20260225-1",
      "excerpt": "Use Risk Factors and disclosures for current risk assessment."
    }
  ]
}
```

Input (`catalyst_research_agent`):
```json
{"ticker": "NVDA", "topic": "catalysts"}
```
Output snippet:
```json
{
  "ticker": "NVDA",
  "topic": "catalysts",
  "context_chunks": [
    {
      "citation_id": "NVDA-8K-20260225-1",
      "excerpt": "Use filing commentary for recent catalysts."
    }
  ]
}
```
What this means:
- The workflow gathered citation-backed evidence per topic before writing.

### 3) `metrics_agent` -> `extract_financial_metrics`
Input snippet:
```json
{"ticker": "NVDA"}
```
Output snippet:
```json
{
  "ticker": "NVDA",
  "metrics": {
    "fiscal_period_end": "2026-01-25",
    "source_form": "10-K",
    "revenue_usd_mn": 215938.0,
    "gross_margin_pct": 71.1,
    "operating_margin_pct": 60.4
  }
}
```
What this means:
- The agent pulled deterministic headline financial values used in deck content.

### 4) `deck_payload_agent` (no tool call; model output)
Input snippet (combined upstream context):
```text
Normalized deck request + topic context chunks + extracted metrics
```
Output snippet:
```json
{
  "ticker": "NVDA",
  "deck_type": "investment_snapshot",
  "audience": "internal_ic",
  "slides": [
    {"title": "Overview", "bullets": ["..."]},
    {"title": "Business Model", "bullets": ["..."]},
    {"title": "Financial Snapshot", "bullets": ["..."]}
  ]
}
```
What this means:
- The orchestrator converted raw evidence into a deck-structured payload.

### 5) `writer_agent` (no tool call; model output)
Input snippet:
```text
Deck payload + evidence/citations + metrics
```
Output snippet:
```markdown
## Deck Draft - NVDA
### Company Overview
- Recent 10-K filed on 2026-02-25 ... (Citation: NVDA-10K-20260225-1)
...
```
What this means:
- A human-readable draft was generated from the structured payload.

### 6) `critic_agent` (no tool call; model output)
Input snippet:
```text
Current draft report
```
Output snippet:
```text
Citations complete. No major issues found.
```
What this means:
- The draft passed critique checks.

### 7) `refiner_agent` -> `exit_loop`
Input snippet:
```json
null
```
Output snippet:
```json
{}
```
Final emitted output snippet:
```markdown
## Deck Draft - NVDA
...
```
What this means:
- Loop terminated and final draft was returned unchanged.

## Simple summary
- Your one-line prompt became a structured deck contract.
- The system fetched filing context for 5 topics.
- It extracted financial metrics for NVDA.
- It assembled payload -> wrote draft -> critiqued draft.
- Critic approved, so refiner exited and returned final deck content.
