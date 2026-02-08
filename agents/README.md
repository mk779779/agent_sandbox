# Report Gen - OLAP Sales Report Loop Agent

An ADK agent that generates and iteratively refines OLAP sales reports using a critic/refiner loop pattern. Built on the [ADK Loop Agents](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/) framework with OpenAI GPT-4o mini via LiteLLM.

It now includes a parameterized OLAP fetch tool backed by a simple in-repo sales fact table:

- Data file: `report_gen/sales_olap.py`
- Tool: `fetch_sales_olap(quarter, subclass, sku, region)`
- Insight-drill tool: `investigate_sales_drilldown(quarter, subclass, region)`
- Final output file: `outputs/reports/latest_report.md` (overwritten each new run)
- Returns:
  - filtered summary (revenue, units, avg price)
  - period context vs previous quarter (when quarter is specified)
  - global min/max revenue (across subclass+SKU in scope)
  - local min/max revenue (by subclass, SKU, or region depending on drill depth)
  - dimensional breakdowns
  - insight-led drill path (driver -> deeper cut -> contrast area)
  - business signal pack (top-2 concentration, driver-vs-laggard gap, regional spread, anomaly candidates)

Current synthetic OLAP scale:
- 192 fact rows
- 4 quarters x 4 regions (NA/EU/APAC/LATAM)
- 4 subclasses x 12 SKUs

## Process Overview

The agent uses a **SequentialAgent** pipeline with a **LoopAgent** inside it:
- `report_gen_initial`: builds the first report draft from tool outputs.
- `report_gen_critic`: checks if the draft meets report quality criteria.
- `report_gen_refiner`: either improves the report or exits when quality is met.
- `save_report_after_loop`: writes final markdown output to disk.

### Phase 1: Initial Draft (runs once)

```text
User prompt ("Q3 revenue report")
        │
        ▼
┌─────────────────────┐
│ report_gen_initial   │  Calls fetch_sales_olap, then writes
│ (LlmAgent)          │  a full structured first-pass report
└────────┬────────────┘
         │ saves draft → state["current_document"]
         ▼
```

### Phase 2: Refinement Loop (up to 3 iterations)

```text
┌──────────────────────────────────────────────────┐
│  report_gen_loop (LoopAgent, max_iterations=3)   │
│                                                  │
│  ┌────────────────────┐                          │
│  │ report_gen_critic   │  Reads state["current_document"]
│  │ (LlmAgent)         │  and checks quality criteria:
│  │                     │    1. Required OLAP report section structure
│  │                     │    2. KPI snapshot with valid metrics
│  │                     │    3. Scoped segmentation + min/max coverage
│  │                     │    4. Insight-led drill path
│  │                     │    5. Quantified impact findings (share/gap/variance)
│  │                     │    6. Risks/caveats explicitly stated
│  │                     │    7. Concrete actions (strong + weak performers)
│  └────────┬───────────┘
│           │ saves feedback → state["criticism"]
│           ▼
│  ┌────────────────────┐
│  │ report_gen_refiner  │  Reads both state keys:
│  │ (LlmAgent)         │
│  │                     │  IF criticism = "No major issues found."
│  │                     │    → calls exit_loop tool (ends loop)
│  │                     │
│  │                     │  ELSE
│  │                     │    → applies feedback, writes improved
│  │                     │      report back to state["current_document"]
│  └────────┬───────────┘
│           │
│           ▼ (next iteration or exit)
└──────────────────────────────────────────────────┘
```

### Phase 3: Save Output (runs once)

After loop completion, an ADK `after_agent_callback` saves the final report to:

- `outputs/reports/latest_report.md`

The filename stays the same and is overwritten on each new run.

### State Flow Summary

| State Key            | Written By        | Read By                  |
|----------------------|-------------------|--------------------------|
| `current_document`   | Initial / Refiner | Critic, Refiner          |
| `criticism`          | Critic            | Refiner                  |

### Exit Condition

The loop ends when **either**:

- The **Critic** responds with exactly `"No major issues found."` and the **Refiner** calls the `exit_loop` tool (which sets `escalate = True`)
- The loop hits the **max 3 iterations** safety limit

## Setup

1. Install dependencies:

   ```bash
   poetry install
   ```

2. Set your OpenAI API key (shell export or `.env`):

   ```bash
   export OPENAI_API_KEY=your-openai-api-key
   ```

3. Optional: remove the `google-cloud-storage < 3.0.0` warning:

   ```bash
   poetry add "google-cloud-storage@^3.0.0"
   ```

## How To Run

1. Start ADK Web with auto-reload:

```bash
poetry run adk web --reload --reload_agents .
```

2. Open `http://localhost:8000`.
3. Select the `report_gen` agent in the UI.
4. Enter a prompt (examples below).
5. Wait for loop completion, then check output file:
   - `outputs/reports/latest_report.md`

## CLI Command Reference

```bash
poetry run adk web --reload --reload_agents .
```

- `--reload`: restarts app on code changes
- `--reload_agents`: refreshes agent discovery on agent/module changes

**Example prompts:**

- "Give me a report based on Q1"
- "Q2 electronics report with min max by SKU"
- "Q4 HOME-001 regional performance and min/max"
