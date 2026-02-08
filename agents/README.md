# Report Gen - OLAP Sales Report Loop Agent

An ADK agent that generates and iteratively refines OLAP sales reports using a critic/refiner loop pattern. Built on the [ADK Loop Agents](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/) framework with OpenAI GPT-4o mini via LiteLLM.

It now includes a parameterized OLAP fetch tool backed by a simple in-repo sales fact table:

- Data file: `report_gen/sales_olap.py`
- Tool: `fetch_sales_olap(quarter, subclass, sku, region)`
- Final output file: `outputs/latest_report.md` (overwritten each new run)
- Returns:
  - filtered summary (revenue, units, avg price)
  - global min/max revenue (across subclass+SKU in scope)
  - local min/max revenue (by subclass, SKU, or region depending on drill depth)
  - dimensional breakdowns

## How the Loop Agent Flow Works

The agent uses a **SequentialAgent** pipeline with a **LoopAgent** inside it. The flow has three phases:

### Phase 1: Initial Draft (runs once)

```text
User prompt ("Q3 revenue report")
        │
        ▼
┌─────────────────────┐
│ report_gen_initial   │  Calls fetch_sales_olap, then writes
│ (LlmAgent)          │  a bare-bones 1-2 sentence report draft
└────────┬────────────┘
         │ saves draft → state["current_document"]
         ▼
```

### Phase 2: Refinement Loop (up to 5 iterations)

```text
┌──────────────────────────────────────────────────┐
│  report_gen_loop (LoopAgent, max_iterations=5)   │
│                                                  │
│  ┌────────────────────┐                          │
│  │ report_gen_critic   │  Reads state["current_document"]
│  │ (LlmAgent)         │  and checks against 5 criteria:
│  │                     │    1. At least 4 sentences
│  │                     │    2. 3+ OLAP metrics covered
│  │                     │    3. At least 1 segmentation/slice
│  │                     │    4. States an insight or trend
│  │                     │    5. Multiline Markdown formatting
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

- `outputs/latest_report.md`

The filename stays the same and is overwritten on each new run.

### State Flow Summary

| State Key            | Written By        | Read By                  |
|----------------------|-------------------|--------------------------|
| `current_document`   | Initial / Refiner | Critic, Refiner          |
| `criticism`          | Critic            | Refiner                  |

### Exit Condition

The loop ends when **either**:

- The **Critic** responds with exactly `"No major issues found."` and the **Refiner** calls the `exit_loop` tool (which sets `escalate = True`)
- The loop hits the **max 5 iterations** safety limit

## Setup

1. Install dependencies with Poetry:

   ```bash
   poetry install
   ```

2. Set your OpenAI API key (via `.env` file or shell export):

   ```bash
   OPENAI_API_KEY=your-openai-api-key
   ```

3. Optional: remove the `google-cloud-storage < 3.0.0` warning:

   ```bash
   poetry add "google-cloud-storage@^3.0.0"
   ```

## Run with ADK Web

```bash
poetry run adk web --reload --reload_agents .
```

Open <http://localhost:8000> in your browser and select the **report_gen** agent.

**Example prompts:**

- "Give me a report based on Q1"
- "Q2 electronics report with min max by SKU"
- "Q4 HOME-001 regional performance and min/max"
