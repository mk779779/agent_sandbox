# Agentic Design Review and Target Architecture

## Objective
Build a report-generation agent that can replace analyst-style OLAP workflows:
- produce an executive summary
- support drill-down by dimension (quarter -> subclass -> SKU -> region/channel/store)
- surface min/max and outliers at global and local scopes
- keep outputs reproducible and auditable

## Current Design (as implemented)
- Orchestration: `SequentialAgent(initial -> loop)`
- Loop internals: `critic` + `refiner` with `exit_loop` stop tool
- Data access: single tool `fetch_sales_olap(quarter, subclass, sku, region)`
- Persistence: writes final markdown to `outputs/latest_report.md`

Files:
- `report_gen/loop_agent.py`
- `report_gen/sales_olap.py`

## Review Findings
### Critical
1. Factual QA is weak
- The critic validates format/coverage, not data correctness or reconciliation.
- Refiner can rewrite wording without re-querying data.
- References: `report_gen/loop_agent.py:119`, `report_gen/loop_agent.py:159`

2. Drill-down is not agentically planned
- Request parsing and drill logic are embedded in prompt behavior, not an explicit query plan.
- No explicit representation of grain, metric set, comparison baseline, or ranking objective.
- Reference: `report_gen/loop_agent.py:91`

### High
3. Tool contract is too narrow for analyst workflows
- Current tool only filters by 4 fields and returns pre-fixed aggregates.
- Missing top-N ranking, variance vs prior period, contribution %, percentile/outlier detection, pagination/windowing.
- Reference: `report_gen/sales_olap.py:93`

4. Data model is static and non-temporal
- Flat in-memory fact list is good for demo, not for production analyst replacement.
- No date grain (month/week/day), versioning, freshness metadata, or source lineage.
- Reference: `report_gen/sales_olap.py:8`

### Medium
5. Save behavior is tied to loop completion path
- Save is mostly triggered on loop completion; partial/failure paths need explicit artifact capture.
- Reference: `report_gen/loop_agent.py:41`, `report_gen/loop_agent.py:68`

## Target Architecture (for Analyst Replacement)
Use a planner-executor-analyst pattern with explicit drill state.

### 1) Planner Agent
Responsibility:
- convert user prompt into `QuerySpec`
- decide metric(s), grain, dimensions, filters, compare periods, ranking intent

Output (state):
- `query_spec`
- `analysis_goal` (`summary`, `drill`, `anomaly`, `comparison`)

### 2) OLAP Executor Tool Layer
Deterministic functions only (no prose):
- `run_query(query_spec) -> table + metadata`
- `drill(query_spec, dimension, member, next_dimension) -> child_query_spec + table`
- `compute_extrema(query_spec, metric, level, scope) -> min/max + context`
- `compute_contribution(query_spec, metric, by_dimension)`
- `compute_period_variance(query_spec, metric, compare_to)`

All functions return:
- data payload
- row count
- query hash
- freshness timestamp

### 3) Analyst Agent
Responsibility:
- convert numeric outputs into insights
- identify drivers and exceptions
- propose next drill steps

Must cite evidence keys (query hash + row ids/group keys).

### 4) Report Composer Agent
Responsibility:
- render final markdown sections
- include global view and drill hierarchy

Required sections:
- Executive Summary
- KPI Snapshot
- Drill Tree
- Min/Max and Outliers
- Key Drivers
- Risks / Data Caveats
- Next Questions

### 5) QA/Policy Agent
Checks:
- every number in report maps to a computed payload
- no unsupported claims
- all requested dimensions answered or explicitly marked unavailable

## State Model
Use structured state keys (not only free text):
- `query_spec`
- `query_history` (list of executed query specs and hashes)
- `result_cache` (hash -> dataframe/json)
- `drill_tree` (parent/child drill lineage)
- `insights` (evidence-linked statements)
- `final_report_markdown`

## Drill-Down Behavior
Expected user flow:
1. "Give me Q1 report" -> global KPIs + subclass ranking
2. "Drill into Electronics" -> SKU view within Electronics
3. "Drill into top SKU by region" -> region split for selected SKU
4. "Show min/max globally vs within Electronics" -> dual-scope extrema table

Agent behavior requirement:
- keep drill context in state
- allow user to jump levels without losing lineage
- persist each drill step in report appendix or artifacts

## Data Layer Recommendations
Short term:
- keep local store but move from hardcoded list to file-backed facts (`csv/parquet`)
- add `date` and derived `month`, `week`, `quarter`

Production target:
- warehouse-backed OLAP (BigQuery/Snowflake/etc.)
- semantic metric layer (single metric definitions)
- typed query schema and validation

## Reliability and Observability
- Log query specs and hashes for each execution
- Save:
  - `outputs/latest_report.md`
  - `outputs/latest_report.json` (machine-readable evidence bundle)
- Add regression tests:
  - filter correctness
  - min/max correctness by scope
  - drill lineage correctness
  - report evidence coverage

## Implementation Plan
1. Introduce `QuerySpec` schema and planner output.
2. Expand tool layer to deterministic analytics functions.
3. Add evidence-linked insight generation.
4. Add QA gate for factual consistency.
5. Add JSON artifact output and test suite.

## Acceptance Criteria
- User can iteratively drill through at least 3 levels in one session.
- Every reported metric is reproducible from saved query payloads.
- Final report includes both global and local min/max with scope labels.
- System returns explicit "cannot answer" when requested grain/dimension is missing.
