"""
OLAP Metrics Report Loop Agent - ADK Example

Based on: https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/#full-example-iterative-document-improvement
"""

from pathlib import Path

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext

from .sales_olap import fetch_sales_olap

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
    tool_context.actions.skip_summarization = True
    return {}


def _save_report_markdown(markdown: str) -> dict:
    """Save markdown to agents/outputs/latest_report.md."""
    agents_dir = Path(__file__).resolve().parents[1]
    output_dir = agents_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "latest_report.md"
    output_path.write_text(markdown, encoding="utf-8")
    print("_save_report_markdown:", markdown)
    return {
        "saved_to": str(output_path),
        "chars_written": len(markdown),
    }


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
    You are a BI analyst generating an OLAP sales report from structured data.

    FIRST: Call the fetch_sales_olap tool with best-effort parameters extracted from the user's prompt.
    - If prompt mentions a quarter (e.g. q1, q2), pass quarter.
    - If prompt mentions subclass or SKU, pass those filters too.
    - If not specified, call without filters to get an overview.

    SECOND: Write a *very basic* first draft report (1-2 simple sentences) grounded in tool output.
    Mention at least one metric and one min/max comparison from the returned data.

    Output *only* the report text. Do not add introductions or explanations.
    """,
    description="Writes the initial OLAP report draft based on the topic, aiming for some initial substance.",
    tools=[fetch_sales_olap],
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

    **Completion Criteria (ALL must be met):**
    1. At least 4 sentences long
    2. Covers at least three OLAP-style metrics (e.g., revenue, orders, AOV, retention)
    3. Includes at least one segmentation or slice (e.g., by region, product, channel, or time)
    4. States one brief insight or trend
    5. Properly formatted as multiline Markdown (not a single line)

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
    Carefully apply the suggestions to improve the 'Current Document'. Output *only* the refined report text.
    Keep all factual values consistent with the data already used in the draft.

    Formatting requirements for the refined report:
    - Use Markdown.
    - Use this exact section structure:
      1) "## Sales Report - <scope>"
      2) "### Summary"
      3) "### Breakdown"
      4) "### Min/Max Analysis"
      5) "### Insight"
    - Use bullets under Breakdown and Min/Max Analysis.
    - Keep line breaks and blank lines between sections.
    - Never output the whole report as a single line.

    Do not add explanations. Always output a non-empty report document.
    """,
    description="Refines the report based on critique, or calls exit_loop if critique indicates completion.",
    tools=[exit_loop],
    output_key=STATE_CURRENT_DOC,
)

# STEP 2: Refinement Loop Agent
report_gen_loop_agent = LoopAgent(
    name="report_gen_loop",
    sub_agents=[report_gen_critic_agent, report_gen_refiner_agent],
    max_iterations=5,
    after_agent_callback=save_report_after_loop,
)

# STEP 3: Overall Sequential Pipeline (root_agent required for adk web)
root_agent = SequentialAgent(
    name="report_gen",
    sub_agents=[report_gen_initial_agent, report_gen_loop_agent],
    description="Writes an initial OLAP report, iteratively refines it with critique, and saves final markdown output programmatically.",
)
