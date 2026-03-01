# Report Gen - OLAP Analyst Agent

An ADK agent for analyst-style OLAP reporting. It does deterministic planning (`QuerySpec` + `AnalysisPlan`), executes drill queries, then writes/refines a report through a critic loop.

## What It Produces

- Final report: `outputs/reports/latest_report.md` (overwritten each run)
- Input data/tools: `report_gen/sales_olap.py`
- Core tools:
  - `build_query_spec(...)`
  - `build_analysis_plan(...)`
  - `execute_query_spec(...)`
  - `investigate_sales_drilldown(...)`
  - `fetch_sales_olap(...)`

Synthetic OLAP scale:
- 192 fact rows
- 4 quarters x 4 regions (NA/EU/APAC/LATAM)
- 4 subclasses x 12 SKUs

## Architecture

- `report_gen_initial`
  - Builds `AnalysisPlan`
  - Executes baseline + pivot evidence queries
  - Drafts first report
- `report_gen_critic`
  - Validates report quality criteria
- `report_gen_refiner`
  - Re-plans/re-executes when critique fails
  - Exits loop when criteria pass

Flow:
1. Initial draft from tool evidence
2. Critic/refiner loop (max 3 iterations)
3. Save final markdown artifact

### Agent Graph

```text
User Prompt
   |
   v
SequentialAgent: report_gen
   |
   +--> LlmAgent: report_gen_initial
   |      |- build_analysis_plan(...)
   |      |- execute_query_spec(...)  [baseline]
   |      |- execute_query_spec(...)  [pivot/contrast]
   |      `- investigate_sales_drilldown(...)
   |
   `--> LoopAgent: report_gen_loop (max 3)
          |
          +--> LlmAgent: report_gen_critic
          |      `- validate report criteria
          |
          `--> LlmAgent: report_gen_refiner
                 |- if pass: exit_loop()
                 `- else: re-plan + re-execute + refine

After loop:
save_report_after_loop -> outputs/reports/latest_report.md
```

## QuerySpec And AnalysisPlan

- `QuerySpec` defines:
  - filters (`quarter`, `region`, `subclass`, `sku`)
  - dimensions/grain
  - metrics
  - comparison mode (previous quarter or none)
  - ranking metric/order/limit
- `AnalysisPlan` defines:
  - objective
  - step-by-step drill path (baseline -> driver drill -> contrast pivot)
  - pivot rules
  - stop rules

This keeps drill logic explicit and auditable instead of prompt-only.

### Example QuerySpec

```json
{
  "filters": {
    "quarter": "Q4",
    "subclass": "Electronics",
    "sku": null,
    "region": null
  },
  "dimensions": ["sku"],
  "metrics": ["revenue", "units", "avg_price"],
  "compare_to": "previous_quarter",
  "ranking": {
    "metric": "revenue",
    "order": "desc",
    "limit": 5
  }
}
```

### Example AnalysisPlan

```json
{
  "analysis_goal": "find_growth_and_risk_drivers",
  "scope_filters": {
    "quarter": "Q4",
    "subclass": "Electronics",
    "sku": null,
    "region": null
  },
  "steps": [
    {
      "step_id": "baseline",
      "objective": "Establish KPI baseline and rank major contributors.",
      "query_spec": {
        "dimensions": ["sku"],
        "metrics": ["revenue", "units", "avg_price", "rows"]
      }
    },
    {
      "step_id": "driver_drill",
      "objective": "Drill into strongest contributor for deeper drivers.",
      "query_spec": {
        "dimensions": ["region"],
        "metrics": ["revenue", "units", "avg_price"]
      }
    },
    {
      "step_id": "contrast_pivot",
      "objective": "Pivot to weakest area for recovery contrast.",
      "query_spec": {
        "dimensions": ["region"],
        "metrics": ["revenue", "units", "avg_price"]
      }
    }
  ],
  "pivot_rules": [
    "If top contributor share < 30%, pivot to region concentration.",
    "If anomalies are present, prioritize anomaly branch."
  ],
  "stop_rules": [
    "Stop after 4+ quantified findings and 2 actionable recommendations."
  ]
}
```

## Report Quality Gate

The critic requires all of these:
1. Exact OLAP report section structure
2. KPI snapshot with valid metrics (`revenue`, `units`, `avg_price`, `rows`)
3. Scoped segmentation plus global/local min-max coverage
4. Explicit drill sequence
5. Quantified findings (share/gap/variance style)
6. Risks/data caveats section
7. Concrete actions for strong and weak performers
8. QuerySpec/AnalysisPlan and pivot usage reflected in analysis

## Setup

1. Install dependencies:

```bash
poetry install
```

2. Set API key:

```bash
export OPENAI_API_KEY=your-openai-api-key
```

### Environment Variables

Required:
- `OPENAI_API_KEY`: OpenAI API key used by ADK/LiteLLM.

You can set it either way:

```bash
export OPENAI_API_KEY=your-openai-api-key
```

Or via `.env` file in this project directory:

```env
OPENAI_API_KEY=your-openai-api-key
```

## Run

```bash
poetry run adk web --reload --reload_agents .
```

Then:
1. Open `http://localhost:8000`
2. Select `report_gen`
3. Submit a prompt
4. Check `outputs/reports/latest_report.md`

## Prompt Examples

- `Q4 full OLAP report with pivots if concentration is weak`
- `Q2 electronics deep dive: driver, laggard, and recovery actions`
- `Q3 APAC performance with global vs local min/max and anomalies`
