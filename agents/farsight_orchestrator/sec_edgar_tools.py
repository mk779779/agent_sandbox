"""Phase 1 SEC EDGAR tools for farsight_orchestrator.

This module intentionally uses a curated EDGAR snapshot so the workflow is
deterministic for local development. The interface mirrors how live ingestion
would be consumed in production.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_DECK_TYPES = {"investment_snapshot", "earnings_update", "risk_brief"}
VALID_AUDIENCES = {"internal_ic", "client", "exec_team"}
VALID_TOPICS = {"overview", "business_model", "financial_snapshot", "risks", "catalysts"}

FILING_CHUNKS: list[dict[str, Any]] = [
    {
        "ticker": "NVDA",
        "filing_type": "10-K",
        "filing_date": "2025-02-21",
        "section": "Business",
        "topic": "overview",
        "excerpt": "NVIDIA provides accelerated computing platforms across data center, gaming, professional visualization, and automotive end markets.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html?doc=/Archives/edgar/data/1045810/000104581025000024/nvda-20250126.htm",
        "citation_id": "NVDA-10K-2025-BUS-1",
    },
    {
        "ticker": "NVDA",
        "filing_type": "10-K",
        "filing_date": "2025-02-21",
        "section": "Business Strategy",
        "topic": "business_model",
        "excerpt": "The company monetizes a hardware-software ecosystem including GPUs, networking, and AI software frameworks.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html?doc=/Archives/edgar/data/1045810/000104581025000024/nvda-20250126.htm",
        "citation_id": "NVDA-10K-2025-BIZMOD-1",
    },
    {
        "ticker": "NVDA",
        "filing_type": "10-K",
        "filing_date": "2025-02-21",
        "section": "Management Discussion and Analysis",
        "topic": "financial_snapshot",
        "excerpt": "Data center demand and AI infrastructure spending were primary drivers of year-over-year growth in revenue.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html?doc=/Archives/edgar/data/1045810/000104581025000024/nvda-20250126.htm",
        "citation_id": "NVDA-10K-2025-FIN-1",
    },
    {
        "ticker": "NVDA",
        "filing_type": "10-K",
        "filing_date": "2025-02-21",
        "section": "Risk Factors",
        "topic": "risks",
        "excerpt": "Results may be affected by concentration in customers, supply chain dependencies, and geopolitical trade restrictions.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html?doc=/Archives/edgar/data/1045810/000104581025000024/nvda-20250126.htm",
        "citation_id": "NVDA-10K-2025-RISK-1",
    },
    {
        "ticker": "NVDA",
        "filing_type": "8-K",
        "filing_date": "2025-11-20",
        "section": "Item 2.02 Results of Operations",
        "topic": "catalysts",
        "excerpt": "The filing includes quarterly financial results and management commentary on forward demand trends.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html",
        "citation_id": "NVDA-8K-2025-CAT-1",
    },
    {
        "ticker": "MSFT",
        "filing_type": "10-K",
        "filing_date": "2025-07-30",
        "section": "Business",
        "topic": "overview",
        "excerpt": "Microsoft operates productivity and business process, intelligent cloud, and personal computing segments.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html",
        "citation_id": "MSFT-10K-2025-BUS-1",
    },
    {
        "ticker": "MSFT",
        "filing_type": "10-K",
        "filing_date": "2025-07-30",
        "section": "Risk Factors",
        "topic": "risks",
        "excerpt": "Cybersecurity, cloud competition, and regulatory scrutiny remain key enterprise risks.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html",
        "citation_id": "MSFT-10K-2025-RISK-1",
    },
    {
        "ticker": "AAPL",
        "filing_type": "10-K",
        "filing_date": "2025-11-01",
        "section": "Business",
        "topic": "overview",
        "excerpt": "Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and services.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html",
        "citation_id": "AAPL-10K-2025-BUS-1",
    },
    {
        "ticker": "AAPL",
        "filing_type": "10-K",
        "filing_date": "2025-11-01",
        "section": "Management Discussion and Analysis",
        "topic": "financial_snapshot",
        "excerpt": "Services growth and product mix shift were noted as material influences on margin profile.",
        "source_url": "https://www.sec.gov/ixviewer/ix.html",
        "citation_id": "AAPL-10K-2025-FIN-1",
    },
]

METRIC_SNAPSHOTS: dict[str, dict[str, Any]] = {
    "NVDA": {
        "fiscal_period": "FY2025",
        "revenue_usd_mn": 130_497.0,
        "gross_margin_pct": 74.3,
        "operating_margin_pct": 62.1,
        "data_center_revenue_mix_pct": 78.0,
    },
    "MSFT": {
        "fiscal_period": "FY2025",
        "revenue_usd_mn": 245_122.0,
        "gross_margin_pct": 69.4,
        "operating_margin_pct": 44.5,
        "cloud_mix_pct": 49.0,
    },
    "AAPL": {
        "fiscal_period": "FY2025",
        "revenue_usd_mn": 391_022.0,
        "gross_margin_pct": 46.8,
        "operating_margin_pct": 30.3,
        "services_mix_pct": 26.0,
    },
}


def _clean_ticker(ticker: str) -> str:
    cleaned = (ticker or "").strip().upper()
    valid = sorted({chunk["ticker"] for chunk in FILING_CHUNKS})
    return cleaned if cleaned in valid else "NVDA"


def _clean_deck_type(deck_type: str) -> str:
    cleaned = (deck_type or "").strip().lower()
    return cleaned if cleaned in VALID_DECK_TYPES else "investment_snapshot"


def _clean_audience(audience: str) -> str:
    cleaned = (audience or "").strip().lower()
    return cleaned if cleaned in VALID_AUDIENCES else "internal_ic"


def _dedupe_citations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    citations: list[dict[str, Any]] = []
    for row in rows:
        citation_id = row["citation_id"]
        if citation_id in seen:
            continue
        seen.add(citation_id)
        citations.append(
            {
                "citation_id": citation_id,
                "filing_type": row["filing_type"],
                "filing_date": row["filing_date"],
                "section": row["section"],
                "source_url": row["source_url"],
            }
        )
    return citations


def _strip_fences(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def _extract_sources_markdown(payload: str) -> str:
    cleaned = _strip_fences(payload)
    if not cleaned:
        return ""
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return cleaned
    if isinstance(parsed, dict):
        value = parsed.get("sources_markdown")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return cleaned


def build_deck_request(
    ticker: str = "NVDA",
    deck_type: str = "investment_snapshot",
    audience: str = "internal_ic",
) -> dict[str, Any]:
    """Validate and normalize deck request input."""
    cleaned_ticker = _clean_ticker(ticker)
    cleaned_deck_type = _clean_deck_type(deck_type)
    cleaned_audience = _clean_audience(audience)

    return {
        "deck_request": {
            "ticker": cleaned_ticker,
            "deck_type": cleaned_deck_type,
            "audience": cleaned_audience,
            "allowed_topics": sorted(VALID_TOPICS),
        }
    }


def build_section_plan(deck_type: str = "investment_snapshot") -> dict[str, Any]:
    """Return a deterministic section plan for phase 1 deck drafts."""
    cleaned_deck_type = _clean_deck_type(deck_type)
    base_sections = [
        {"section_id": "overview", "title": "Company Overview", "topic": "overview"},
        {"section_id": "business_model", "title": "Business Model", "topic": "business_model"},
        {"section_id": "financial_snapshot", "title": "Financial Snapshot", "topic": "financial_snapshot"},
        {"section_id": "risks", "title": "Key Risks", "topic": "risks"},
        {"section_id": "catalysts", "title": "Recent Catalysts", "topic": "catalysts"},
    ]
    if cleaned_deck_type == "risk_brief":
        base_sections = [
            {"section_id": "overview", "title": "Company Overview", "topic": "overview"},
            {"section_id": "risks", "title": "Key Risks", "topic": "risks"},
            {"section_id": "catalysts", "title": "Risk Catalysts", "topic": "catalysts"},
            {"section_id": "financial_snapshot", "title": "Financial Capacity", "topic": "financial_snapshot"},
        ]
    return {"section_plan": {"deck_type": cleaned_deck_type, "sections": base_sections}}


def get_filing_context(
    ticker: str = "NVDA",
    topic: str = "overview",
    max_chunks: int = 3,
) -> dict[str, Any]:
    """Retrieve filing excerpts for a specific topic with citations."""
    cleaned_ticker = _clean_ticker(ticker)
    cleaned_topic = (topic or "").strip().lower()
    if cleaned_topic not in VALID_TOPICS:
        cleaned_topic = "overview"
    limit = max(1, min(int(max_chunks or 3), 5))

    rows = [
        row
        for row in FILING_CHUNKS
        if row["ticker"] == cleaned_ticker and row["topic"] == cleaned_topic
    ]
    rows = sorted(rows, key=lambda row: row["filing_date"], reverse=True)[:limit]
    context_chunks = [
        {
            "citation_id": row["citation_id"],
            "excerpt": row["excerpt"],
            "section": row["section"],
            "filing_type": row["filing_type"],
            "filing_date": row["filing_date"],
        }
        for row in rows
    ]
    return {
        "ticker": cleaned_ticker,
        "topic": cleaned_topic,
        "context_chunks": context_chunks,
        "citations": _dedupe_citations(rows),
    }


def extract_financial_metrics(ticker: str = "NVDA") -> dict[str, Any]:
    """Return compact financial snapshot metrics for deck drafting."""
    cleaned_ticker = _clean_ticker(ticker)
    snapshot = METRIC_SNAPSHOTS.get(cleaned_ticker)
    if not snapshot:
        return {"error": f"No metric snapshot available for ticker {cleaned_ticker}."}

    return {
        "ticker": cleaned_ticker,
        "metrics": snapshot,
        "highlights": [
            f"{cleaned_ticker} {snapshot['fiscal_period']} revenue: ${snapshot['revenue_usd_mn']:,.0f}M",
            f"Gross margin: {snapshot['gross_margin_pct']}%",
            f"Operating margin: {snapshot['operating_margin_pct']}%",
        ],
    }


def build_sources_markdown(ticker: str = "NVDA") -> dict[str, Any]:
    """Build a markdown source appendix from all known filing citations."""
    cleaned_ticker = _clean_ticker(ticker)
    rows = [row for row in FILING_CHUNKS if row["ticker"] == cleaned_ticker]
    citations = _dedupe_citations(sorted(rows, key=lambda row: row["filing_date"], reverse=True))

    lines = [f"## Sources - {cleaned_ticker}"]
    for item in citations:
        lines.append(
            f"- [{item['citation_id']}] {item['filing_type']} {item['filing_date']} "
            f"({item['section']}): {item['source_url']}"
        )
    return {"sources_markdown": "\n".join(lines), "citations": citations}


def save_deck_artifacts(
    deck_markdown: str = "",
    deck_data_json: str = "",
    sources_markdown: str = "",
    ticker: str = "NVDA",
) -> dict[str, Any]:
    """Persist phase 1 deck artifacts under outputs."""
    cleaned_ticker = _clean_ticker(ticker)
    base_dir = (
        Path(__file__).resolve().parents[2]
        / "outputs"
        / "farsight"
        / cleaned_ticker.lower()
    )
    base_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {"artifact_dir": str(base_dir)}

    cleaned_markdown = _strip_fences(deck_markdown)
    if cleaned_markdown:
        deck_path = base_dir / "latest_deck_draft.md"
        deck_path.write_text(cleaned_markdown, encoding="utf-8")
        result["deck_markdown_path"] = str(deck_path)

    cleaned_json = _strip_fences(deck_data_json)
    if cleaned_json:
        data_path = base_dir / "latest_deck_data.json"
        try:
            parsed = json.loads(cleaned_json)
            data_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        except json.JSONDecodeError:
            data_path.write_text(cleaned_json, encoding="utf-8")
        result["deck_data_json_path"] = str(data_path)

    cleaned_sources = _extract_sources_markdown(sources_markdown)
    if cleaned_sources:
        sources_path = base_dir / "latest_sources.md"
        sources_path.write_text(cleaned_sources, encoding="utf-8")
        result["sources_markdown_path"] = str(sources_path)

    return result
