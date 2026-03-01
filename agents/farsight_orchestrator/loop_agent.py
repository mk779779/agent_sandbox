"""Farsight-style phase 1 deck orchestration with ADK."""

from __future__ import annotations

import json

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext

from .sec_edgar_tools import (
    build_deck_request,
    build_sources_markdown,
    extract_financial_metrics,
    get_filing_context,
    save_deck_artifacts,
)
from .observability import record_artifact_save, setup_otel, start_span

OPENAI_MODEL = "openai/gpt-4o-mini"
setup_otel()

STATE_REQUEST = "deck_request"
STATE_OVERVIEW = "overview_context"
STATE_BIZ = "business_model_context"
STATE_FIN = "financial_context"
STATE_RISKS = "risk_context"
STATE_CATALYSTS = "catalyst_context"
STATE_METRICS = "metrics_context"
STATE_DECK_JSON = "deck_data_json"
STATE_CURRENT_DOC = "current_document"
STATE_CRITICISM = "criticism"

COMPLETION_PHRASE = "Citations complete. No major issues found."


def _resolve_state_text(state, key: str) -> str:
    value = state.get(key) if hasattr(state, "get") else None
    if isinstance(value, str) and value.strip():
        return value

    state_dict = state.to_dict() if hasattr(state, "to_dict") else dict(state or {})
    for state_key, state_value in state_dict.items():
        if state_key.endswith(f".{key}") and isinstance(state_value, str) and state_value.strip():
            return state_value
    return ""


def _resolve_ticker(state) -> str:
    request = _resolve_state_text(state, STATE_REQUEST)
    if not request:
        return "NVDA"
    try:
        parsed = json.loads(request)
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, dict):
        request_obj = parsed.get("deck_request", {})
        ticker = request_obj.get("ticker") if isinstance(request_obj, dict) else None
        if isinstance(ticker, str) and ticker.strip():
            return ticker.strip().upper()
    if '"ticker": "AAPL"' in request:
        return "AAPL"
    if '"ticker": "MSFT"' in request:
        return "MSFT"
    return "NVDA"


def _save_outputs(state) -> dict:
    with start_span("workflow.save_outputs"):
        ticker = _resolve_ticker(state)
        sources_payload = build_sources_markdown(ticker=ticker)
        sources_markdown = sources_payload.get("sources_markdown", "")
        result = save_deck_artifacts(
            deck_markdown=_resolve_state_text(state, STATE_CURRENT_DOC),
            deck_data_json=_resolve_state_text(state, STATE_DECK_JSON),
            sources_markdown=sources_markdown,
            ticker=ticker,
        )
        if result.get("deck_markdown_path"):
            record_artifact_save("deck_markdown", "ok")
        if result.get("deck_data_json_path"):
            record_artifact_save("deck_data_json", "ok")
        if result.get("sources_markdown_path"):
            record_artifact_save("sources_markdown", "ok")
        return result


def exit_loop(tool_context: ToolContext):
    """Exit refinement loop after completion phrase."""
    with start_span("workflow.exit_loop"):
        _save_outputs(tool_context.state or {})
        tool_context.actions.escalate = True
        return {}


def save_after_loop(callback_context: CallbackContext):
    """Persist latest deck outputs after loop completion."""
    with start_span("workflow.after_loop"):
        _save_outputs(callback_context.state)
        return None


request_agent = LlmAgent(
    name="request_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="default",
    instruction="""
    You normalize user request into a phase-1 deck contract.

    Task:
    1) Infer ticker, deck_type, audience.
    2) Call build_deck_request exactly once.
    3) Return only tool output JSON.

    Defaults:
    - ticker: NVDA
    - deck_type: investment_snapshot
    - audience: internal_ic
    """,
    tools=[build_deck_request],
    output_key=STATE_REQUEST,
)


overview_agent = LlmAgent(
    name="overview_research_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use deck_request to call get_filing_context exactly once with topic='overview'.
    Return only tool output JSON.
    """,
    tools=[get_filing_context],
    output_key=STATE_OVERVIEW,
)


business_model_agent = LlmAgent(
    name="business_model_research_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use deck_request to call get_filing_context exactly once with topic='business_model'.
    Return only tool output JSON.
    """,
    tools=[get_filing_context],
    output_key=STATE_BIZ,
)


financial_agent = LlmAgent(
    name="financial_research_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use deck_request to call get_filing_context exactly once with topic='financial_snapshot'.
    Return only tool output JSON.
    """,
    tools=[get_filing_context],
    output_key=STATE_FIN,
)


risk_agent = LlmAgent(
    name="risk_research_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use deck_request to call get_filing_context exactly once with topic='risks'.
    Return only tool output JSON.
    """,
    tools=[get_filing_context],
    output_key=STATE_RISKS,
)


catalyst_agent = LlmAgent(
    name="catalyst_research_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use deck_request to call get_filing_context exactly once with topic='catalysts'.
    Return only tool output JSON.
    """,
    tools=[get_filing_context],
    output_key=STATE_CATALYSTS,
)


research_parallel_agent = ParallelAgent(
    name="research_parallel_agent",
    sub_agents=[overview_agent, business_model_agent, financial_agent, risk_agent, catalyst_agent],
)


metrics_agent = LlmAgent(
    name="metrics_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    Use deck_request to call extract_financial_metrics once.
    Return only tool output JSON.
    """,
    tools=[extract_financial_metrics],
    output_key=STATE_METRICS,
)


deck_payload_agent = LlmAgent(
    name="deck_payload_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    You build structured deck payload JSON from phase-1 SEC context.

    Inputs:
    - deck_request: {{deck_request}}
    - overview_context: {{overview_context}}
    - business_model_context: {{business_model_context}}
    - financial_context: {{financial_context}}
    - risk_context: {{risk_context}}
    - catalyst_context: {{catalyst_context}}
    - metrics_context: {{metrics_context}}

    Output strict JSON only with this shape:
    {
      "ticker": "...",
      "deck_type": "...",
      "audience": "...",
      "slides": [
        {"title":"...", "bullets":["..."], "citations":["..."]}
      ]
    }

    Rules:
    - Use only provided context and metrics.
    - Every bullet must reference at least one citation id in the same slide.
    - Do not add fields outside the required schema.
    - Return JSON only.
    """,
    output_key=STATE_DECK_JSON,
)


writer_agent = LlmAgent(
    name="writer_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction="""
    You are writing a phase-1 investment deck draft.

    Inputs:
    - deck_request: {{deck_request}}
    - overview_context: {{overview_context}}
    - business_model_context: {{business_model_context}}
    - financial_context: {{financial_context}}
    - risk_context: {{risk_context}}
    - catalyst_context: {{catalyst_context}}
    - metrics_context: {{metrics_context}}
    - deck_data_json: {{deck_data_json}}

    Output markdown only with exact structure:
    1) ## Deck Draft - <ticker>
    2) ### Company Overview
    3) ### Business Model
    4) ### Financial Snapshot
    5) ### Key Risks
    6) ### Recent Catalysts
    7) ### Discussion Prompts

    Rules:
    - Keep each section concise with bullet points.
    - Include at least one citation id per section in [CITATION_ID] format.
    - Use only facts from provided state.
    - No placeholders.
    """,
    output_key=STATE_CURRENT_DOC,
)


critic_agent = LlmAgent(
    name="critic_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    include_contents="none",
    instruction=f"""
    Review this deck draft:
    {{current_document}}

    Pass criteria:
    1) All required section headers are present.
    2) Each section has at least one bullet.
    3) Every section includes at least one [CITATION_ID].
    4) No unsupported claims beyond provided SEC context/metrics.

    If ALL criteria pass, respond exactly:
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
    Current document:
    {{current_document}}

    Critique:
    {{criticism}}

    If critique equals exactly "{COMPLETION_PHRASE}":
    - Call exit_loop
    - Return current document unchanged

    Otherwise:
    - Refine the document to satisfy critique.
    - Keep exact required section structure.
    - Keep facts grounded in provided state.
    - Output markdown only.
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
    name="farsight_orchestrator",
    sub_agents=[
        request_agent,
        research_parallel_agent,
        metrics_agent,
        deck_payload_agent,
        writer_agent,
        refinement_loop_agent,
    ],
    description="Phase-1 Farsight-style deck workflow using SEC EDGAR context, citation checks, and saved artifacts.",
)
