"""
Deterministic SEC-style KPI tools for ADK multi-agent orchestration demos.

These tools simulate a governed SQL layer by using fixed in-memory tables and
strictly validated query specs.
"""

from __future__ import annotations

from typing import Any

VALID_METRICS = {
    "revenue",
    "gross_margin_pct",
    "operating_margin_pct",
    "fcf",
    "net_debt",
}
VALID_COMPARE_TO = {"qoq", "yoy", "peer"}
VALID_PERIODS = {"2025Q2", "2025Q3", "2025Q4"}

# Simple governed KPI store at company-period grain.
KPI_FACTS: list[dict[str, Any]] = [
    {
        "ticker": "MSFT",
        "period": "2025Q2",
        "sector": "Software",
        "peer_set": "mega_cap_software",
        "revenue": 67800.0,
        "gross_margin_pct": 68.5,
        "operating_margin_pct": 43.7,
        "fcf": 21800.0,
        "net_debt": -54000.0,
    },
    {
        "ticker": "MSFT",
        "period": "2025Q3",
        "sector": "Software",
        "peer_set": "mega_cap_software",
        "revenue": 70200.0,
        "gross_margin_pct": 67.9,
        "operating_margin_pct": 42.9,
        "fcf": 21200.0,
        "net_debt": -56000.0,
    },
    {
        "ticker": "MSFT",
        "period": "2025Q4",
        "sector": "Software",
        "peer_set": "mega_cap_software",
        "revenue": 73850.0,
        "gross_margin_pct": 68.2,
        "operating_margin_pct": 43.2,
        "fcf": 24100.0,
        "net_debt": -59000.0,
    },
    {
        "ticker": "AAPL",
        "period": "2025Q2",
        "sector": "Hardware",
        "peer_set": "mega_cap_hardware",
        "revenue": 90750.0,
        "gross_margin_pct": 45.9,
        "operating_margin_pct": 30.2,
        "fcf": 23100.0,
        "net_debt": 81000.0,
    },
    {
        "ticker": "AAPL",
        "period": "2025Q3",
        "sector": "Hardware",
        "peer_set": "mega_cap_hardware",
        "revenue": 85400.0,
        "gross_margin_pct": 44.8,
        "operating_margin_pct": 29.1,
        "fcf": 19800.0,
        "net_debt": 84500.0,
    },
    {
        "ticker": "AAPL",
        "period": "2025Q4",
        "sector": "Hardware",
        "peer_set": "mega_cap_hardware",
        "revenue": 96800.0,
        "gross_margin_pct": 46.2,
        "operating_margin_pct": 31.0,
        "fcf": 25700.0,
        "net_debt": 79000.0,
    },
    {
        "ticker": "GOOGL",
        "period": "2025Q2",
        "sector": "Internet",
        "peer_set": "mega_cap_internet",
        "revenue": 84200.0,
        "gross_margin_pct": 57.8,
        "operating_margin_pct": 32.7,
        "fcf": 18900.0,
        "net_debt": -98000.0,
    },
    {
        "ticker": "GOOGL",
        "period": "2025Q3",
        "sector": "Internet",
        "peer_set": "mega_cap_internet",
        "revenue": 86550.0,
        "gross_margin_pct": 57.1,
        "operating_margin_pct": 31.8,
        "fcf": 17600.0,
        "net_debt": -100500.0,
    },
    {
        "ticker": "GOOGL",
        "period": "2025Q4",
        "sector": "Internet",
        "peer_set": "mega_cap_internet",
        "revenue": 90200.0,
        "gross_margin_pct": 57.9,
        "operating_margin_pct": 32.5,
        "fcf": 20400.0,
        "net_debt": -103500.0,
    },
]

# Segment/driver table to support root-cause decomposition.
SEGMENT_FACTS: list[dict[str, Any]] = [
    {"ticker": "MSFT", "period": "2025Q3", "dimension": "segment", "key": "Productivity", "revenue": 25800.0, "op_margin_pct": 48.0},
    {"ticker": "MSFT", "period": "2025Q3", "dimension": "segment", "key": "Cloud", "revenue": 31200.0, "op_margin_pct": 46.4},
    {"ticker": "MSFT", "period": "2025Q3", "dimension": "segment", "key": "Personal Computing", "revenue": 13200.0, "op_margin_pct": 23.1},
    {"ticker": "MSFT", "period": "2025Q4", "dimension": "segment", "key": "Productivity", "revenue": 27100.0, "op_margin_pct": 48.3},
    {"ticker": "MSFT", "period": "2025Q4", "dimension": "segment", "key": "Cloud", "revenue": 33850.0, "op_margin_pct": 46.1},
    {"ticker": "MSFT", "period": "2025Q4", "dimension": "segment", "key": "Personal Computing", "revenue": 12900.0, "op_margin_pct": 21.6},
    {"ticker": "AAPL", "period": "2025Q3", "dimension": "segment", "key": "iPhone", "revenue": 43500.0, "op_margin_pct": 34.0},
    {"ticker": "AAPL", "period": "2025Q3", "dimension": "segment", "key": "Services", "revenue": 24200.0, "op_margin_pct": 41.5},
    {"ticker": "AAPL", "period": "2025Q3", "dimension": "segment", "key": "Wearables", "revenue": 17700.0, "op_margin_pct": 20.3},
    {"ticker": "AAPL", "period": "2025Q4", "dimension": "segment", "key": "iPhone", "revenue": 51100.0, "op_margin_pct": 35.2},
    {"ticker": "AAPL", "period": "2025Q4", "dimension": "segment", "key": "Services", "revenue": 25800.0, "op_margin_pct": 42.4},
    {"ticker": "AAPL", "period": "2025Q4", "dimension": "segment", "key": "Wearables", "revenue": 19900.0, "op_margin_pct": 20.8},
    {"ticker": "GOOGL", "period": "2025Q3", "dimension": "segment", "key": "Ads", "revenue": 64400.0, "op_margin_pct": 38.8},
    {"ticker": "GOOGL", "period": "2025Q3", "dimension": "segment", "key": "Cloud", "revenue": 10950.0, "op_margin_pct": 13.4},
    {"ticker": "GOOGL", "period": "2025Q3", "dimension": "segment", "key": "Other Bets", "revenue": 1200.0, "op_margin_pct": -58.0},
    {"ticker": "GOOGL", "period": "2025Q4", "dimension": "segment", "key": "Ads", "revenue": 66600.0, "op_margin_pct": 39.2},
    {"ticker": "GOOGL", "period": "2025Q4", "dimension": "segment", "key": "Cloud", "revenue": 12200.0, "op_margin_pct": 15.0},
    {"ticker": "GOOGL", "period": "2025Q4", "dimension": "segment", "key": "Other Bets", "revenue": 1400.0, "op_margin_pct": -51.5},
]

PEER_BENCHMARKS: dict[str, dict[str, float]] = {
    "mega_cap_software": {
        "revenue": 66500.0,
        "gross_margin_pct": 65.4,
        "operating_margin_pct": 35.8,
        "fcf": 17500.0,
        "net_debt": -14500.0,
    },
    "mega_cap_hardware": {
        "revenue": 84200.0,
        "gross_margin_pct": 40.5,
        "operating_margin_pct": 24.2,
        "fcf": 18600.0,
        "net_debt": 42000.0,
    },
    "mega_cap_internet": {
        "revenue": 70400.0,
        "gross_margin_pct": 52.0,
        "operating_margin_pct": 27.0,
        "fcf": 14900.0,
        "net_debt": -35000.0,
    },
}


def _parse_csv(raw: str) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _normalize_ticker(ticker: str) -> str | None:
    if not ticker:
        return None
    cleaned = ticker.strip().upper()
    valid = sorted({row["ticker"] for row in KPI_FACTS})
    return cleaned if cleaned in valid else None


def _normalize_period(period: str) -> str | None:
    if not period:
        return None
    cleaned = period.strip().upper().replace(" ", "")
    return cleaned if cleaned in VALID_PERIODS else None


def _find_kpi_row(ticker: str, period: str) -> dict[str, Any] | None:
    for row in KPI_FACTS:
        if row["ticker"] == ticker and row["period"] == period:
            return row
    return None


def _previous_period(period: str) -> str | None:
    order = ["2025Q2", "2025Q3", "2025Q4"]
    if period not in order:
        return None
    idx = order.index(period)
    if idx == 0:
        return None
    return order[idx - 1]


def _pct_delta(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round(((current - previous) / abs(previous)) * 100.0, 2)


def _metric_direction(metric: str) -> str:
    # For net_debt, lower is better.
    if metric == "net_debt":
        return "lower_is_better"
    return "higher_is_better"


def build_investigation_request(
    ticker: str = "MSFT",
    period: str = "2025Q4",
    metrics: str = "revenue,gross_margin_pct,operating_margin_pct,fcf,net_debt",
    compare_to: str = "qoq,peer",
) -> dict[str, Any]:
    """Validate and normalize user request into a strict investigation contract."""
    cleaned_ticker = _normalize_ticker(ticker)
    cleaned_period = _normalize_period(period)

    if not cleaned_ticker:
        return {
            "error": f"Unsupported ticker '{ticker}'.",
            "available_tickers": sorted({row['ticker'] for row in KPI_FACTS}),
        }

    if not cleaned_period:
        return {
            "error": f"Unsupported period '{period}'.",
            "available_periods": sorted(VALID_PERIODS),
        }

    metric_candidates = [m.lower() for m in _parse_csv(metrics)]
    cleaned_metrics = [m for m in metric_candidates if m in VALID_METRICS]
    if not cleaned_metrics:
        cleaned_metrics = ["revenue", "gross_margin_pct", "operating_margin_pct", "fcf"]

    compare_candidates = [c.lower() for c in _parse_csv(compare_to)]
    cleaned_compare = [c for c in compare_candidates if c in VALID_COMPARE_TO]
    if not cleaned_compare:
        cleaned_compare = ["qoq", "peer"]

    return {
        "request": {
            "ticker": cleaned_ticker,
            "period": cleaned_period,
            "metrics": cleaned_metrics,
            "compare_to": cleaned_compare,
        }
    }


def build_finance_analysis_plan(
    ticker: str = "MSFT",
    period: str = "2025Q4",
    metrics: str = "revenue,gross_margin_pct,operating_margin_pct,fcf,net_debt",
    compare_to: str = "qoq,peer",
) -> dict[str, Any]:
    """Build a deterministic analysis plan with explicit evidence steps."""
    request_result = build_investigation_request(ticker=ticker, period=period, metrics=metrics, compare_to=compare_to)
    if "error" in request_result:
        return request_result

    request = request_result["request"]
    return {
        "analysis_plan": {
            "objective": "detect_kpi_change_diagnose_root_causes_recommend_actions",
            "request": request,
            "steps": [
                {
                    "step_id": "baseline",
                    "objective": "Fetch KPI baseline for requested period.",
                    "tool": "execute_kpi_baseline_query",
                },
                {
                    "step_id": "variance",
                    "objective": "Compute QoQ and YoY variance for selected KPIs.",
                    "tool": "execute_kpi_variance_query",
                },
                {
                    "step_id": "peer",
                    "objective": "Benchmark KPIs versus peer set medians.",
                    "tool": "execute_kpi_peer_query",
                },
                {
                    "step_id": "root_cause",
                    "objective": "Rank segment drivers and weak spots.",
                    "tool": "rank_root_causes",
                },
            ],
            "stop_rules": [
                "At least 3 quantified findings with evidence refs.",
                "At least 2 concrete actions (one growth, one risk mitigation).",
            ],
        }
    }


def execute_kpi_baseline_query(
    ticker: str = "MSFT",
    period: str = "2025Q4",
    metrics: str = "revenue,gross_margin_pct,operating_margin_pct,fcf,net_debt",
) -> dict[str, Any]:
    """Return KPI baseline values and a synthetic query id (SQL evidence token)."""
    request_result = build_investigation_request(ticker=ticker, period=period, metrics=metrics)
    if "error" in request_result:
        return request_result

    request = request_result["request"]
    row = _find_kpi_row(request["ticker"], request["period"])
    if not row:
        return {"message": "No baseline rows found."}

    selected = {metric: row[metric] for metric in request["metrics"]}
    return {
        "query_id": f"baseline_{request['ticker']}_{request['period']}",
        "filters": {"ticker": request["ticker"], "period": request["period"]},
        "kpis": selected,
        "peer_set": row["peer_set"],
    }


def execute_kpi_variance_query(
    ticker: str = "MSFT",
    period: str = "2025Q4",
    metrics: str = "revenue,gross_margin_pct,operating_margin_pct,fcf,net_debt",
) -> dict[str, Any]:
    """Return QoQ/YoY variance for selected metrics with anomaly signals."""
    request_result = build_investigation_request(ticker=ticker, period=period, metrics=metrics, compare_to="qoq,yoy")
    if "error" in request_result:
        return request_result

    request = request_result["request"]
    current = _find_kpi_row(request["ticker"], request["period"])
    if not current:
        return {"message": "No current rows found."}

    prev_period = _previous_period(request["period"])
    prev = _find_kpi_row(request["ticker"], prev_period) if prev_period else None

    rows = []
    for metric in request["metrics"]:
        current_val = float(current[metric])
        prev_val = float(prev[metric]) if prev else 0.0
        delta = round(current_val - prev_val, 2)
        delta_pct = _pct_delta(current_val, prev_val)
        zscore = round(delta_pct / 12.0, 2)
        anomaly_flag = abs(zscore) >= 1.0
        rows.append(
            {
                "metric": metric,
                "current": current_val,
                "previous": prev_val,
                "qoq_delta": delta,
                "qoq_delta_pct": delta_pct,
                "zscore": zscore,
                "directionality": _metric_direction(metric),
                "anomaly_flag": anomaly_flag,
            }
        )

    return {
        "query_id": f"variance_{request['ticker']}_{request['period']}",
        "filters": {"ticker": request["ticker"], "period": request["period"], "previous_period": prev_period},
        "variance_rows": rows,
    }


def execute_kpi_peer_query(
    ticker: str = "MSFT",
    period: str = "2025Q4",
    metrics: str = "revenue,gross_margin_pct,operating_margin_pct,fcf,net_debt",
) -> dict[str, Any]:
    """Return peer comparison deltas for the selected KPIs."""
    request_result = build_investigation_request(ticker=ticker, period=period, metrics=metrics, compare_to="peer")
    if "error" in request_result:
        return request_result

    request = request_result["request"]
    current = _find_kpi_row(request["ticker"], request["period"])
    if not current:
        return {"message": "No current rows found."}

    peer_values = PEER_BENCHMARKS.get(current["peer_set"], {})
    peer_rows = []
    for metric in request["metrics"]:
        company_val = float(current[metric])
        peer_val = float(peer_values.get(metric, 0.0))
        delta = round(company_val - peer_val, 2)
        directionality = _metric_direction(metric)
        if directionality == "lower_is_better":
            # Improvement semantics: positive means better than peer for lower-is-better metrics.
            # Denominator uses peer magnitude for consistent "vs peer" interpretation.
            if peer_val == 0:
                delta_pct = 0.0
            else:
                delta_pct = round(((peer_val - company_val) / abs(peer_val)) * 100.0, 2)
        else:
            delta_pct = _pct_delta(company_val, peer_val)
        peer_rows.append(
            {
                "metric": metric,
                "company": company_val,
                "peer_median": peer_val,
                "peer_delta": delta,
                "peer_delta_pct": delta_pct,
                "directionality": directionality,
            }
        )

    return {
        "query_id": f"peer_{request['ticker']}_{request['period']}",
        "filters": {"ticker": request["ticker"], "period": request["period"], "peer_set": current["peer_set"]},
        "peer_rows": peer_rows,
    }


def detect_kpi_anomalies(
    ticker: str = "MSFT",
    period: str = "2025Q4",
    metrics: str = "revenue,gross_margin_pct,operating_margin_pct,fcf,net_debt",
) -> dict[str, Any]:
    """Detect anomalous KPI shifts from deterministic variance output."""
    variance = execute_kpi_variance_query(ticker=ticker, period=period, metrics=metrics)
    if "variance_rows" not in variance:
        return variance

    anomaly_rows = [row for row in variance["variance_rows"] if row["anomaly_flag"]]
    return {
        "query_id": f"anomaly_{ticker.upper()}_{period.upper()}",
        "anomaly_rows": anomaly_rows,
        "source_query_id": variance["query_id"],
    }


def rank_root_causes(
    ticker: str = "MSFT",
    period: str = "2025Q4",
    focus_metric: str = "revenue",
) -> dict[str, Any]:
    """Rank segment-level contributors for the target metric."""
    cleaned_ticker = _normalize_ticker(ticker)
    cleaned_period = _normalize_period(period)
    if not cleaned_ticker:
        return {"error": f"Unsupported ticker '{ticker}'."}
    if not cleaned_period:
        return {"error": f"Unsupported period '{period}'."}

    current_rows = [
        row
        for row in SEGMENT_FACTS
        if row["ticker"] == cleaned_ticker and row["period"] == cleaned_period
    ]
    prev_period = _previous_period(cleaned_period)
    prev_rows = [
        row
        for row in SEGMENT_FACTS
        if prev_period and row["ticker"] == cleaned_ticker and row["period"] == prev_period
    ]

    prev_map = {row["key"]: row for row in prev_rows}
    findings = []
    for row in current_rows:
        prev_revenue = float(prev_map.get(row["key"], {}).get("revenue", 0.0))
        revenue = float(row["revenue"])
        delta = round(revenue - prev_revenue, 2)
        findings.append(
            {
                "dimension": row["dimension"],
                "key": row["key"],
                "revenue": revenue,
                "qoq_delta": delta,
                "qoq_delta_pct": _pct_delta(revenue, prev_revenue),
                "op_margin_pct": float(row["op_margin_pct"]),
            }
        )

    ranked = sorted(findings, key=lambda item: item["qoq_delta"], reverse=True)
    negative_findings = sorted(
        [item for item in findings if item["qoq_delta"] < 0],
        key=lambda item: item["qoq_delta"],
    )
    bottom_drivers = negative_findings[:2]
    return {
        "query_id": f"root_cause_{cleaned_ticker}_{cleaned_period}",
        "focus_metric": focus_metric,
        "top_drivers": ranked[:2],
        "bottom_drivers": bottom_drivers,
    }


def map_causes_to_playbooks(
    ticker: str = "MSFT",
    period: str = "2025Q4",
    focus_metric: str = "revenue",
) -> dict[str, Any]:
    """Map detected causes to deterministic action playbooks."""
    causes = rank_root_causes(ticker=ticker, period=period, focus_metric=focus_metric)
    if "top_drivers" not in causes:
        return causes

    actions = []
    for driver in causes["top_drivers"]:
        actions.append(
            {
                "action_type": "scale_winner",
                "target": driver["key"],
                "owner": "Segment GM",
                "expected_impact": f"Protect +2% to +4% {focus_metric} contribution next quarter",
                "rationale": f"{driver['key']} contributed {driver['qoq_delta']} QoQ change.",
            }
        )

    for laggard in causes["bottom_drivers"]:
        actions.append(
            {
                "action_type": "recover_laggard",
                "target": laggard["key"],
                "owner": "Finance BP + Ops",
                "expected_impact": f"Recover 1% to 2% {focus_metric} drag within 2 quarters",
                "rationale": f"{laggard['key']} posted {laggard['qoq_delta']} QoQ change.",
            }
        )

    return {
        "query_id": f"playbook_{ticker.upper()}_{period.upper()}",
        "actions": actions,
        "source_query_id": causes["query_id"],
    }
