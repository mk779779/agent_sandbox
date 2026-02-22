"""
SEC KPI Orchestrator - ADK multi-agent workflow.

Pattern mirrors report_gen: sequential pipeline with a critic/refiner loop,
but adds a parallel query fan-out stage for baseline/variance/peer evidence.
"""

from pathlib import Path

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext

from .finance_tools import (
    build_finance_analysis_plan,
    build_investigation_request,
    detect_kpi_anomalies,
    execute_kpi_baseline_query,
    execute_kpi_peer_query,
    execute_kpi_variance_query,
    map_causes_to_playbooks,
    rank_root_causes,
)

OPENAI_MODEL = "openai/gpt-4o-mini"

STATE_REQUEST = "request_contract"
STATE_PLAN = "analysis_plan"
STATE_BASELINE = "baseline_result"
STATE_VARIANCE = "variance_result"
STATE_PEER = "peer_result"
STATE_ANOMALIES = "anomaly_result"
STATE_ROOT_CAUSES = "root_cause_result"
STATE_ACTIONS = "action_result"
STATE_CURRENT_DOC = "current_document"
STATE_CRITICISM = "criticism"

COMPLETION_PHRASE = "Evidence complete. No major issues found."


def _resolve_state_text(state, key: str) -> str:
    value = state.get(key) if hasattr(state, "get") else None
    if isinstance(value, str) and value.strip():
        return value

    state_dict = state.to_dict() if hasattr(state, "to_dict") else dict(state or {})
    for state_key, state_value in state_dict.items():
        if state_key.endswith(f".{key}") and isinstance(state_value, str) and state_value.strip():
            return state_value
    return ""


def _save_outputs(markdown: str, payload: str = "") -> dict:
    base_dir = Path(__file__).resolve().parents[1] / "outputs" / "reports"
    base_dir.mkdir(parents=True, exist_ok=True)

    report_path = base_dir / "latest_sec_kpi_report.md"
    report_path.write_text(markdown, encoding="utf-8")

    result = {
        "saved_report": str(report_path),
        "report_chars": len(markdown),
    }
    if payload.strip():
        payload_path = base_dir / "latest_sec_kpi_payload.json"
        payload_path.write_text(payload, encoding="utf-8")
        result["saved_payload"] = str(payload_path)

    print("_save_outputs:", result)
    return result


def exit_loop(tool_context: ToolContext):
    """Call only after critic confirms completion criteria."""
    markdown = _resolve_state_text(tool_context.state or {}, STATE_CURRENT_DOC)
    payload = _resolve_state_text(tool_context.state or {}, STATE_ACTIONS)
    if markdown:
        _save_outputs(markdown, payload)
    tool_context.actions.escalate = True
    return {}


def save_after_loop(callback_context: CallbackContext):
    """Save report deterministically at the end of the loop."""
    state = callback_context.state
    markdown = _resolve_state_text(state, STATE_CURRENT_DOC)
    payload = _resolve_state_text(state, STATE_ACTIONS)
    if markdown:
        _save_outputs(markdown, payload)
    return None


request_agent = LlmAgent(
    name="request_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="default",
    instruction="""
    You are an enterprise finance request normalizer.

    Task:
    1) Infer ticker, period, metrics, and compare_to from user prompt.
    2) Call build_investigation_request once with best-effort parameters.
    3) Return only the validated request JSON.

    Defaults when unspecified:
    - ticker: MSFT
    - period: 2025Q4
    - metrics: revenue,gross_margin_pct,operating_margin_pct,fcf,net_debt
    - compare_to: qoq,peer
    """,
    tools=[build_investigation_request],
    output_key=STATE_REQUEST,
)


plan_agent = LlmAgent(
    name="plan_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    You are a finance analysis planner.

    Request contract:
    {{request_contract}}

    Task:
    1) Extract ticker, period, metrics, compare_to from request_contract.
    2) Call build_finance_analysis_plan.
    3) Return only the plan JSON.
    """,
    tools=[build_finance_analysis_plan],
    output_key=STATE_PLAN,
)


baseline_query_agent = LlmAgent(
    name="baseline_query_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use request_contract to call execute_kpi_baseline_query once.
    Return only tool output JSON.
    """,
    tools=[execute_kpi_baseline_query],
    output_key=STATE_BASELINE,
)


variance_query_agent = LlmAgent(
    name="variance_query_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use request_contract to call execute_kpi_variance_query once.
    Return only tool output JSON.
    """,
    tools=[execute_kpi_variance_query],
    output_key=STATE_VARIANCE,
)


peer_query_agent = LlmAgent(
    name="peer_query_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use request_contract to call execute_kpi_peer_query once.
    Return only tool output JSON.
    """,
    tools=[execute_kpi_peer_query],
    output_key=STATE_PEER,
)


query_parallel_agent = ParallelAgent(
    name="query_parallel_agent",
    sub_agents=[baseline_query_agent, variance_query_agent, peer_query_agent],
)


anomaly_agent = LlmAgent(
    name="anomaly_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use request_contract to call detect_kpi_anomalies once.
    Return only tool output JSON.
    """,
    tools=[detect_kpi_anomalies],
    output_key=STATE_ANOMALIES,
)


root_cause_agent = LlmAgent(
    name="root_cause_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use request_contract to call rank_root_causes once.
    Focus metric should default to revenue unless user asks otherwise.
    Return only tool output JSON.
    """,
    tools=[rank_root_causes],
    output_key=STATE_ROOT_CAUSES,
)


action_agent = LlmAgent(
    name="action_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use request_contract to call map_causes_to_playbooks once.
    Focus metric should default to revenue unless user asks otherwise.
    Return only tool output JSON.
    """,
    tools=[map_causes_to_playbooks],
    output_key=STATE_ACTIONS,
)


writer_agent = LlmAgent(
    name="writer_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    You are writing a finance KPI investigation report.

    Inputs:
    - request_contract: {{request_contract}}
    - analysis_plan: {{analysis_plan}}
    - baseline_result: {{baseline_result}}
    - variance_result: {{variance_result}}
    - peer_result: {{peer_result}}
    - anomaly_result: {{anomaly_result}}
    - root_cause_result: {{root_cause_result}}
    - action_result: {{action_result}}

    Output a markdown report with this exact structure:
    1) ## SEC KPI Report - <ticker> <period>
    2) ### Executive Summary
    3) ### KPI Change Table
    4) ### Root-Cause Breakdown
    5) ### Peer Context
    6) ### Recommended Actions
    7) ### Risks and Caveats
    8) ### Evidence

    Rules:
    - Include at least 3 quantified findings.
    - Include at least 2 concrete actions.
    - Each finding must cite query_id evidence.
    - Do not invent fields outside provided tool output.
    - Output only report markdown.
    """,
    output_key=STATE_CURRENT_DOC,
)


critic_agent = LlmAgent(
    name="critic_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction=f"""
    Review this report:
    {{current_document}}

    Pass criteria:
    1) Required section structure is present.
    2) At least 3 quantified findings.
    3) At least 2 concrete recommendations.
    4) Evidence section references query IDs.
    5) No unsupported claims.

    If ALL pass, respond exactly:
    {COMPLETION_PHRASE}

    Else return concise actionable critique only.
    """,
    output_key=STATE_CRITICISM,
)


refiner_agent = LlmAgent(
    name="refiner_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction=f"""
    Current report:
    {{current_document}}

    Critique:
    {{criticism}}

    If critique equals exactly "{COMPLETION_PHRASE}":
    - Call exit_loop
    - Return current report unchanged

    Otherwise:
    - Improve the report to satisfy critique
    - Keep all claims grounded in provided state/tool outputs
    - Keep exact required section structure
    - Return only refined markdown report
    """,
    tools=[exit_loop],
    output_key=STATE_CURRENT_DOC,
)


refinement_loop_agent = LoopAgent(
    name="refinement_loop_agent",
    sub_agents=[critic_agent, refiner_agent],
    max_iterations=3,
    after_agent_callback=save_after_loop,
)


root_agent = SequentialAgent(
    name="sec_kpi_orchestrator",
    sub_agents=[
        request_agent,
        plan_agent,
        query_parallel_agent,
        anomaly_agent,
        root_cause_agent,
        action_agent,
        writer_agent,
        refinement_loop_agent,
    ],
    description="SEC KPI multi-agent workflow with parallel SQL evidence, diagnosis, and iterative report refinement.",
)
