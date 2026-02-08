"""
OLAP Metrics Report Loop Agent - ADK Example

Based on: https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/#full-example-iterative-document-improvement
"""

from pathlib import Path

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext

from .sales_olap import fetch_sales_olap, investigate_sales_drilldown

# --- Constants ---
# Using LiteLLM format for OpenAI models
OPENAI_MODEL = "openai/gpt-4o-mini"

# --- State Keys ---
STATE_CURRENT_DOC = "current_document"
STATE_CRITICISM = "criticism"
# Define the exact phrase the Critic should use to signal completion
COMPLETION_PHRASE = "No major issues found."


# --- Tool Definition ---
def _resolve_current_document(state) -> str:
    """Get current document from direct or namespaced state keys."""
    markdown = state.get(STATE_CURRENT_DOC) if hasattr(state, "get") else None
    if isinstance(markdown, str) and markdown.strip():
        return markdown

    state_dict = state.to_dict() if hasattr(state, "to_dict") else dict(state or {})
    for key, value in state_dict.items():
        if key.endswith(f".{STATE_CURRENT_DOC}") and isinstance(value, str) and value.strip():
            return value
    return ""


def exit_loop(tool_context: ToolContext):
    """Call this function ONLY when the critique indicates no further changes are needed, signaling the iterative process should end."""
    print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
    # Deterministic local persistence on normal loop completion.
    markdown = _resolve_current_document(tool_context.state or {})
    if markdown:
        _save_report_markdown(markdown)
    else:
        print("exit_loop: no non-empty current_document found in state.")
    tool_context.actions.escalate = True
    return {}


def _save_report_markdown(markdown: str) -> dict:
    """Save markdown to agents/outputs/reports/latest_report.md."""
    agents_dir = Path(__file__).resolve().parents[1]
    output_dir = agents_dir / "outputs" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "latest_report.md"
    output_path.write_text(markdown, encoding="utf-8")
    result = {
        "saved_to": str(output_path),
        "chars_written": len(markdown),
    }

    # If content appears sensitive, also persist to dedicated location.
    lowered = markdown.lower()
    sensitive_markers = ("sensitive", "confidential", "private", "internal only")
    if any(marker in lowered for marker in sensitive_markers):
        sensitive_dir = output_dir / "sensitive"
        sensitive_dir.mkdir(parents=True, exist_ok=True)
        sensitive_path = sensitive_dir / "latest_report.md"
        sensitive_path.write_text(markdown, encoding="utf-8")
        result["sensitive_saved_to"] = str(sensitive_path)

    print("_save_report_markdown:", result)
    return result


def save_report_after_loop(callback_context: CallbackContext):
    """Programmatically persist the latest report after loop completion."""
    state = callback_context.state
    markdown = _resolve_current_document(state)
    if not markdown:
        keys = list(state.to_dict().keys()) if hasattr(state, "to_dict") else []
        print("save_report_after_loop: no non-empty current_document found in state keys:", keys)
        return None
    _save_report_markdown(markdown)
    return None


# --- Agent Definitions ---

# STEP 1: Initial Writer Agent (Runs ONCE at the beginning)
report_gen_initial_agent = LlmAgent(
    name="report_gen_initial",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="default",  # receives user message from adk web chat
    instruction="""
    You are a BI analyst generating a production-style OLAP sales report from structured data.

    FIRST: Call the investigate_sales_drilldown tool with best-effort parameters extracted from the user's prompt.
    - If prompt mentions a quarter (e.g. q1, q2), pass quarter.
    - If prompt mentions subclass or region, pass those filters too.
    - If not specified, call without filters to get an overview.
    - Use its staged outputs (baseline -> primary driver -> drill within driver -> contrast area).

    SECOND: Write a complete first-pass report grounded in tool output.
    Use this exact section structure:
    1) "## OLAP Performance Report - <scope>"
    2) "### Executive Summary"
    3) "### KPI Snapshot"
    4) "### Drivers and Variance"
    5) "### Drilldown Findings"
    6) "### Risks and Data Caveats"
    7) "### Recommended Actions"

    Requirements:
    - Use multiline Markdown and include bullets in Drivers and Variance, Drilldown Findings, and Recommended Actions.
    - In KPI Snapshot, include at least three available metrics: revenue, units, avg_price, rows.
    - Include explicit context for the scope and segmentation used (quarter/region/subclass/sku).
    - Include both global and local min/max statements from tool output with clear scope labels.
    - Show a full drill path: baseline -> primary driver -> deeper cut -> contrast area.
    - Include at least four quantified findings (for example share %, gap $, concentration %, best-vs-worst spread, or period delta when available).
    - If anomaly candidates are present, call out at least one with the related dimension keys.
    - Include at least two concrete actions: one to scale a strong performer and one to recover a weak performer.
    - Keep claims auditable: every numeric claim must be tied to returned tool values.
    - Do not use unsupported fields unless explicitly available in tool output.
    - No placeholders.

    Output *only* the report text. Do not add introductions or explanations.
    """,
    description="Writes a full first-pass OLAP report grounded in tool data.",
    tools=[investigate_sales_drilldown, fetch_sales_olap],
    output_key=STATE_CURRENT_DOC,
)

# STEP 2a: Critic Agent (Inside the Refinement Loop)
report_gen_critic_agent = LlmAgent(
    name="report_gen_critic",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction=f"""
    You are a Constructive Critic AI reviewing an OLAP metrics report draft.

    **Document to Review:**
    ```
    {{{{current_document}}}}
    ```

    **Allowed Dataset Metrics and Dimensions:**
    - Metrics: revenue, units, avg_price, rows
    - Dimensions: quarter, region, subclass, sku
    - Not available unless explicitly computed from tool output: orders, channel, retention

    **Completion Criteria (ALL must be met):**
    1. Uses this exact section structure:
       - "## OLAP Performance Report - <scope>"
       - "### Executive Summary"
       - "### KPI Snapshot"
       - "### Drivers and Variance"
       - "### Drilldown Findings"
       - "### Risks and Data Caveats"
       - "### Recommended Actions"
    2. KPI Snapshot includes at least three valid metrics from this dataset (revenue, units, avg_price, rows)
    3. Includes at least one explicit segmentation/slice using valid dimensions (quarter, region, subclass, sku)
    4. Includes both global and local min/max with scope labels
    5. Shows an explicit drill sequence (baseline -> driver -> deeper cut -> contrast area)
    6. Contains at least four quantified findings (share, gap, concentration, spread, or period delta when available)
    7. Includes anomaly discussion if anomaly candidates are provided by tool output
    8. Includes at least two concrete recommended actions (one offensive, one defensive)
    9. Includes a caveat/limitation section grounded in available data scope
    10. Proper multiline Markdown; no placeholders ("TBD", "N/A", "placeholder", "<...>")
    11. Contains no unsupported claims/fields (e.g., channel or retention when not present in data)

    **Task:**
    Check the document against the criteria above.

    IF any criteria is NOT met, provide specific feedback on what to add or improve.
    Output *only* the critique text.

    IF ALL criteria are met, respond *exactly* with: "{COMPLETION_PHRASE}"
    """,
    description="Reviews the current report, providing critique if clear improvements are needed, otherwise signals completion.",
    output_key=STATE_CRITICISM,
)

# STEP 2b: Refiner/Exiter Agent (Inside the Refinement Loop)
report_gen_refiner_agent = LlmAgent(
    name="report_gen_refiner",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction=f"""
    You are a BI analyst refining an OLAP sales report based on feedback OR exiting the process.
    **Current Document:**
    ```
    {{{{current_document}}}}
    ```
    **Critique/Suggestions:**
    {{{{criticism}}}}

    **Task:**
    Analyze the 'Critique/Suggestions'.
    IF the critique is *exactly* "{COMPLETION_PHRASE}":
    You MUST call the 'exit_loop' function.
    Then output the current document unchanged: {{{{current_document}}}}
    Never return an empty response in this branch.
    ELSE (the critique contains actionable feedback):
    FIRST: Call investigate_sales_drilldown to refresh insight-led drill context.
    - Infer quarter/subclass/region from current document or critique when possible.
    - If unsure, call investigate_sales_drilldown without filters.
    SECOND: If needed for numeric detail, call fetch_sales_olap for supporting breakdown values.
    THIRD: Carefully apply the suggestions to improve the 'Current Document'. Output *only* the refined report text.
    Keep all factual values consistent with the data already used in the draft.
    Do NOT invent metrics or dimensions.
    If data for a requested metric/dimension is unavailable, state that explicitly.
    Ensure insights are prioritized by impact and include concrete recommendations for both upside scaling and downside recovery.
    Ensure the final document satisfies all critic completion criteria.

    Formatting requirements for the refined report:
    - Use Markdown.
    - Use this exact section structure:
      1) "## OLAP Performance Report - <scope>"
      2) "### Executive Summary"
      3) "### KPI Snapshot"
      4) "### Drivers and Variance"
      5) "### Drilldown Findings"
      6) "### Risks and Data Caveats"
      7) "### Recommended Actions"
    - Use bullets under Drivers and Variance, Drilldown Findings, and Recommended Actions.
    - Keep line breaks and blank lines between sections.
    - Never output the whole report as a single line.

    Do not add explanations. Always output a non-empty report document.
    """,
    description="Refines the report based on critique, or calls exit_loop if critique indicates completion.",
    tools=[exit_loop, investigate_sales_drilldown, fetch_sales_olap],
    output_key=STATE_CURRENT_DOC,
)

# STEP 2: Refinement Loop Agent
report_gen_loop_agent = LoopAgent(
    name="report_gen_loop",
    sub_agents=[report_gen_critic_agent, report_gen_refiner_agent],
    max_iterations=3,
    after_agent_callback=save_report_after_loop,
)

# STEP 3: Overall Sequential Pipeline (root_agent required for adk web)
root_agent = SequentialAgent(
    name="report_gen",
    sub_agents=[report_gen_initial_agent, report_gen_loop_agent],
    description="Writes an initial OLAP report, iteratively refines it with critique, and saves final markdown output.",
)
