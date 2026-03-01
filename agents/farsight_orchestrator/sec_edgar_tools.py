"""Phase 1 SEC EDGAR tools for farsight_orchestrator.

Tools attempt live SEC retrieval first, then fall back to curated data for
local reliability.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .observability import traced_tool

VALID_DECK_TYPES = {"investment_snapshot", "earnings_update", "risk_brief"}
VALID_AUDIENCES = {"internal_ic", "client", "exec_team"}
VALID_TOPICS = {"overview", "business_model", "financial_snapshot", "risks", "catalysts"}
SEC_CONTACT_EMAIL = os.getenv("SEC_CONTACT_EMAIL", "masacodingdev@gmail.com")
DEFAULT_SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", f"farsight-orchestrator/phase1 ({SEC_CONTACT_EMAIL})")
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

_TICKER_CIK_CACHE: dict[str, str] | None = None
CURATED_TICKER_CIK = {
    "NVDA": "0001045810",
    "MSFT": "0000789019",
    "AAPL": "0000320193",
}

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
    if cleaned.isalpha() and 1 <= len(cleaned) <= 6:
        return cleaned
    return "NVDA"


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


def _http_get_json(url: str) -> dict[str, Any]:
    headers = {
        "User-Agent": DEFAULT_SEC_USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
    }
    if "@" in SEC_CONTACT_EMAIL:
        headers["From"] = SEC_CONTACT_EMAIL
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _ticker_cik_map() -> dict[str, str]:
    global _TICKER_CIK_CACHE
    if _TICKER_CIK_CACHE is not None:
        return _TICKER_CIK_CACHE
    mapping: dict[str, str] = dict(CURATED_TICKER_CIK)
    try:
        payload = _http_get_json(SEC_TICKERS_URL)
        for row in payload.values():
            ticker = str(row.get("ticker", "")).upper().strip()
            cik_str = str(row.get("cik_str", "")).strip()
            if ticker and cik_str:
                mapping[ticker] = cik_str.zfill(10)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        # Keep curated fallback map when SEC endpoint is not reachable.
        pass
    _TICKER_CIK_CACHE = mapping
    return mapping


def _resolve_cik(ticker: str) -> str | None:
    return _ticker_cik_map().get(ticker)


def _build_filing_url(cik: str, accession: str, primary_doc: str) -> str:
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession.replace('-', '')}/{primary_doc}"
    )


def _fetch_recent_filings(ticker: str) -> list[dict[str, Any]]:
    cik = _resolve_cik(ticker)
    if not cik:
        return []
    payload = _http_get_json(SEC_SUBMISSIONS_URL.format(cik=cik))
    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    filings: list[dict[str, Any]] = []
    for idx, form in enumerate(forms):
        if form not in {"10-K", "10-Q", "8-K"}:
            continue
        filing_date = filing_dates[idx] if idx < len(filing_dates) else ""
        accession = accession_numbers[idx] if idx < len(accession_numbers) else ""
        primary_doc = primary_docs[idx] if idx < len(primary_docs) else "index.html"
        filing_url = _build_filing_url(cik, accession, primary_doc)
        filings.append(
            {
                "ticker": ticker,
                "filing_type": form,
                "filing_date": filing_date,
                "section": "Filing",
                "source_url": filing_url,
                "accession_number": accession,
            }
        )
        if len(filings) >= 25:
            break
    return filings


def _topic_filter(topic: str, filing_type: str) -> bool:
    if topic in {"overview", "business_model", "risks"}:
        return filing_type in {"10-K", "10-Q"}
    if topic == "financial_snapshot":
        return filing_type in {"10-K", "10-Q"}
    if topic == "catalysts":
        return filing_type == "8-K"
    return True


def _live_excerpt(topic: str, row: dict[str, Any]) -> str:
    form = row["filing_type"]
    date = row["filing_date"]
    if topic == "overview":
        return f"Recent {form} filed on {date}; use this filing as primary company disclosure context."
    if topic == "business_model":
        return f"{form} filed on {date}; review business section and MD&A for operating model updates."
    if topic == "financial_snapshot":
        return f"{form} filed on {date}; use reported statements and MD&A for latest financial profile."
    if topic == "risks":
        return f"{form} filed on {date}; use Risk Factors and disclosures for current risk assessment."
    return f"{form} filed on {date}; use filing commentary for recent catalysts."


def _live_context(ticker: str, topic: str, limit: int) -> dict[str, Any] | None:
    try:
        filings = _fetch_recent_filings(ticker)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None
    if not filings:
        return None

    rows = [row for row in filings if _topic_filter(topic, row["filing_type"])]
    rows = rows[:limit]
    if not rows:
        return None

    context_chunks = []
    citations = []
    for idx, row in enumerate(rows, start=1):
        citation_id = (
            f"{ticker}-{row['filing_type'].replace('-', '')}-"
            f"{row['filing_date'].replace('-', '')}-{idx}"
        )
        section_name = "Item 2.02/8-K Disclosure" if row["filing_type"] == "8-K" else "Filing Disclosure"
        context_chunks.append(
            {
                "citation_id": citation_id,
                "excerpt": _live_excerpt(topic, row),
                "section": section_name,
                "filing_type": row["filing_type"],
                "filing_date": row["filing_date"],
            }
        )
        citations.append(
            {
                "citation_id": citation_id,
                "filing_type": row["filing_type"],
                "filing_date": row["filing_date"],
                "section": section_name,
                "source_url": row["source_url"],
            }
        )

    return {
        "ticker": ticker,
        "topic": topic,
        "context_chunks": context_chunks,
        "citations": citations,
        "data_mode": "live_sec",
    }


def _latest_usd_fact(payload: dict[str, Any], tags: list[str]) -> tuple[float, str, str] | None:
    facts = payload.get("facts", {}).get("us-gaap", {})
    best: tuple[float, str, str] | None = None
    for tag in tags:
        unit_rows = facts.get(tag, {}).get("units", {}).get("USD", [])
        for row in unit_rows:
            val = row.get("val")
            form = row.get("form", "")
            if val is None or form not in {"10-K", "10-Q"}:
                continue
            end = str(row.get("end", ""))
            if best is None or end > best[1]:
                best = (float(val), end, form)
    return best


def _live_metrics(ticker: str) -> dict[str, Any] | None:
    cik = _resolve_cik(ticker)
    if not cik:
        return None
    try:
        payload = _http_get_json(SEC_COMPANY_FACTS_URL.format(cik=cik))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None

    revenue = _latest_usd_fact(
        payload,
        ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    )
    gross_profit = _latest_usd_fact(payload, ["GrossProfit"])
    operating_income = _latest_usd_fact(payload, ["OperatingIncomeLoss"])

    if not revenue:
        return None

    revenue_val, revenue_end, revenue_form = revenue
    gross_margin_pct = round((gross_profit[0] / revenue_val) * 100.0, 1) if gross_profit else None
    operating_margin_pct = round((operating_income[0] / revenue_val) * 100.0, 1) if operating_income else None

    metrics = {
        "fiscal_period_end": revenue_end,
        "source_form": revenue_form,
        "revenue_usd_mn": round(revenue_val / 1_000_000.0, 1),
    }
    if gross_margin_pct is not None:
        metrics["gross_margin_pct"] = gross_margin_pct
    if operating_margin_pct is not None:
        metrics["operating_margin_pct"] = operating_margin_pct

    return {
        "ticker": ticker,
        "metrics": metrics,
        "highlights": [
            f"{ticker} latest reported revenue: ${metrics['revenue_usd_mn']:,.1f}M ({revenue_form}, period end {revenue_end})",
            f"Gross margin: {gross_margin_pct}%" if gross_margin_pct is not None else "Gross margin not available from latest SEC facts.",
            f"Operating margin: {operating_margin_pct}%" if operating_margin_pct is not None else "Operating margin not available from latest SEC facts.",
        ],
        "citations": [
            {
                "citation_id": f"{ticker}-COMPANYFACTS-{revenue_end.replace('-', '')}",
                "filing_type": revenue_form,
                "filing_date": revenue_end,
                "section": "SEC Company Facts",
                "source_url": SEC_COMPANY_FACTS_URL.format(cik=cik),
            }
        ],
        "data_mode": "live_sec",
    }


@traced_tool("build_deck_request")
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


@traced_tool("build_section_plan")
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


@traced_tool("get_filing_context")
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

    live = _live_context(cleaned_ticker, cleaned_topic, limit)
    if live:
        return live

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
        "data_mode": "curated_fallback",
    }


@traced_tool("extract_financial_metrics")
def extract_financial_metrics(ticker: str = "NVDA") -> dict[str, Any]:
    """Return compact financial snapshot metrics for deck drafting."""
    cleaned_ticker = _clean_ticker(ticker)
    live = _live_metrics(cleaned_ticker)
    if live:
        return live

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
        "data_mode": "curated_fallback",
    }


@traced_tool("build_sources_markdown")
def build_sources_markdown(ticker: str = "NVDA") -> dict[str, Any]:
    """Build a markdown source appendix from all known filing citations."""
    cleaned_ticker = _clean_ticker(ticker)
    live = _live_context(cleaned_ticker, "overview", 5)
    if live:
        citations = live["citations"]
    else:
        rows = [row for row in FILING_CHUNKS if row["ticker"] == cleaned_ticker]
        citations = _dedupe_citations(sorted(rows, key=lambda row: row["filing_date"], reverse=True))

    lines = [f"## Sources - {cleaned_ticker}"]
    for item in citations:
        lines.append(
            f"- [{item['citation_id']}] {item['filing_type']} {item['filing_date']} "
            f"({item['section']}): {item['source_url']}"
        )
    return {
        "sources_markdown": "\n".join(lines),
        "citations": citations,
        "data_mode": "live_sec" if live else "curated_fallback",
    }


@traced_tool("save_deck_artifacts")
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
