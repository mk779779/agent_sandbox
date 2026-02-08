"""
Simple OLAP-style sales data store and query helpers.
"""

from typing import Any

# Flat fact-table shape keeps this simple and easy to filter/aggregate.
# Deterministic synthetic generation gives us richer OLAP scale for meaningful insights.
QUARTERS = ("Q1", "Q2", "Q3", "Q4")
QUARTER_FACTORS = {"Q1": 0.94, "Q2": 1.00, "Q3": 1.07, "Q4": 1.17}
REGION_FACTORS = {"NA": 1.18, "EU": 1.0, "APAC": 1.08, "LATAM": 0.82}

SUBCLASS_SKUS: dict[str, list[dict[str, Any]]] = {
    "Electronics": [
        {"sku": "ELEC-001", "base_units": 165, "base_price": 235.0},
        {"sku": "ELEC-002", "base_units": 145, "base_price": 208.0},
        {"sku": "ELEC-003", "base_units": 112, "base_price": 282.0},
    ],
    "Home": [
        {"sku": "HOME-001", "base_units": 198, "base_price": 152.0},
        {"sku": "HOME-002", "base_units": 172, "base_price": 134.0},
        {"sku": "HOME-003", "base_units": 126, "base_price": 176.0},
    ],
    "Outdoors": [
        {"sku": "OUT-001", "base_units": 118, "base_price": 184.0},
        {"sku": "OUT-002", "base_units": 96, "base_price": 204.0},
        {"sku": "OUT-003", "base_units": 88, "base_price": 226.0},
    ],
    "Beauty": [
        {"sku": "BEAU-001", "base_units": 186, "base_price": 72.0},
        {"sku": "BEAU-002", "base_units": 164, "base_price": 86.0},
        {"sku": "BEAU-003", "base_units": 132, "base_price": 102.0},
    ],
}


def _build_sales_olap_facts() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for quarter in QUARTERS:
        quarter_idx = QUARTERS.index(quarter)
        quarter_factor = QUARTER_FACTORS[quarter]
        for region, region_factor in REGION_FACTORS.items():
            region_idx = list(REGION_FACTORS.keys()).index(region)
            for subclass, sku_specs in SUBCLASS_SKUS.items():
                subclass_idx = list(SUBCLASS_SKUS.keys()).index(subclass)
                for sku_idx, spec in enumerate(sku_specs):
                    mix_adjust = 1 + ((quarter_idx + region_idx + subclass_idx + sku_idx) % 4 - 1.5) * 0.04
                    units = int(spec["base_units"] * quarter_factor * region_factor * mix_adjust)
                    units = max(units, 28)
                    price_adjust = 1 + (quarter_idx * 0.012) + (region_idx * 0.006) + (sku_idx * 0.01)
                    price = spec["base_price"] * price_adjust

                    # Inject a few realistic problem/opportunity pockets for analyst detection.
                    if quarter == "Q3" and region == "LATAM" and spec["sku"] == "OUT-003":
                        units = int(units * 0.68)
                    if quarter == "Q4" and region == "APAC" and spec["sku"] == "ELEC-003":
                        units = int(units * 1.22)
                        price *= 1.05
                    if quarter == "Q2" and region == "EU" and spec["sku"] == "HOME-002":
                        price *= 0.93

                    rows.append(
                        {
                            "quarter": quarter,
                            "region": region,
                            "subclass": subclass,
                            "sku": spec["sku"],
                            "units": units,
                            "revenue": int(round(units * price)),
                        }
                    )
    return rows


SALES_OLAP_FACTS: list[dict[str, Any]] = _build_sales_olap_facts()

VALID_QUARTERS = {"Q1", "Q2", "Q3", "Q4"}
VALID_DIMENSIONS = {"quarter", "region", "subclass", "sku"}
VALID_METRICS = {"revenue", "units", "avg_price", "rows"}


def _normalize_quarter(quarter: str):
    if not quarter:
        return None
    cleaned = quarter.strip().upper().replace(" ", "")
    if cleaned in VALID_QUARTERS:
        return cleaned
    if cleaned in {"1", "QTR1", "QUARTER1"}:
        return "Q1"
    if cleaned in {"2", "QTR2", "QUARTER2"}:
        return "Q2"
    if cleaned in {"3", "QTR3", "QUARTER3"}:
        return "Q3"
    if cleaned in {"4", "QTR4", "QUARTER4"}:
        return "Q4"
    return None


def _aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        k = tuple(row[key] for key in keys)
        if k not in buckets:
            buckets[k] = {
                "key": {dim: row[dim] for dim in keys},
                "revenue": 0,
                "units": 0,
            }
        buckets[k]["revenue"] += row["revenue"]
        buckets[k]["units"] += row["units"]

    for bucket in buckets.values():
        units = bucket["units"] or 1
        bucket["avg_price"] = round(bucket["revenue"] / units, 2)
    return list(buckets.values())


def _parse_csv_values(raw: str) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _sanitize_dimensions(raw: str) -> list[str]:
    parsed = [p.lower() for p in _parse_csv_values(raw)]
    dims = [d for d in parsed if d in VALID_DIMENSIONS]
    return dims or ["subclass"]


def _sanitize_metrics(raw: str) -> list[str]:
    parsed = [p.lower() for p in _parse_csv_values(raw)]
    metrics = [m for m in parsed if m in VALID_METRICS]
    return metrics or ["revenue", "units", "avg_price"]


def _min_max(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        return {"min": None, "max": None}
    ordered = sorted(entries, key=lambda x: x["revenue"])
    return {"min": ordered[0], "max": ordered[-1]}


def fetch_sales_olap(
    quarter: str = "",
    subclass: str = "",
    sku: str = "",
    region: str = "",
) -> dict[str, Any]:
    """
    Fetch OLAP sales facts by dimensions and return summary + min/max comparisons.

    Args:
        quarter: Optional quarter filter (Q1-Q4).
        subclass: Optional subclass filter (e.g. Electronics, Home).
        sku: Optional SKU filter (e.g. ELEC-001).
        region: Optional region filter (e.g. NA, EU).
    """
    normalized_quarter = _normalize_quarter(quarter)
    if quarter and not normalized_quarter:
        return {
            "error": f"Unsupported quarter '{quarter}'. Use Q1, Q2, Q3, or Q4.",
            "available_quarters": sorted(VALID_QUARTERS),
        }

    cleaned_subclass = subclass.strip() if subclass else None
    cleaned_sku = sku.strip().upper() if sku else None
    cleaned_region = region.strip().upper() if region else None

    scope_rows = [
        r
        for r in SALES_OLAP_FACTS
        if (not normalized_quarter or r["quarter"] == normalized_quarter)
    ]
    filtered_rows = [
        r
        for r in scope_rows
        if (not cleaned_subclass or r["subclass"].lower() == cleaned_subclass.lower())
        and (not cleaned_sku or r["sku"] == cleaned_sku)
        and (not cleaned_region or r["region"] == cleaned_region)
    ]

    if not filtered_rows:
        return {
            "filters": {
                "quarter": normalized_quarter,
                "subclass": cleaned_subclass,
                "sku": cleaned_sku,
                "region": cleaned_region,
            },
            "message": "No matching sales rows found for these filters.",
        }

    summary = {
        "rows": len(filtered_rows),
        "revenue": sum(r["revenue"] for r in filtered_rows),
        "units": sum(r["units"] for r in filtered_rows),
    }
    summary["avg_price"] = round(summary["revenue"] / max(summary["units"], 1), 2)

    # Global comparison: subclass+sku revenue across the same quarter scope.
    global_min_max = _min_max(_aggregate(scope_rows, ("subclass", "sku")))

    # Local comparison changes by how deep the user drills.
    if cleaned_sku:
        local_level = "region_for_sku"
        local_entries = _aggregate(filtered_rows, ("region",))
    elif cleaned_subclass:
        local_level = "sku_within_subclass"
        subclass_rows = [r for r in scope_rows if r["subclass"].lower() == cleaned_subclass.lower()]
        local_entries = _aggregate(subclass_rows, ("sku",))
    else:
        local_level = "subclass"
        local_entries = _aggregate(scope_rows, ("subclass",))
    local_min_max = _min_max(local_entries)

    region_breakdown = _aggregate(filtered_rows, ("region",))
    subclass_breakdown = _aggregate(filtered_rows, ("subclass",))
    sku_breakdown = _aggregate(filtered_rows, ("sku",))

    return {
        "filters": {
            "quarter": normalized_quarter,
            "subclass": cleaned_subclass,
            "sku": cleaned_sku,
            "region": cleaned_region,
        },
        "summary": summary,
        "global_min_max_revenue": global_min_max,
        "local_min_max_revenue": {
            "level": local_level,
            **local_min_max,
        },
        "breakdown": {
            "by_region": region_breakdown,
            "by_subclass": subclass_breakdown,
            "by_sku": sku_breakdown,
        },
        "available_dimensions": {
            "quarter": sorted({r["quarter"] for r in SALES_OLAP_FACTS}),
            "subclass": sorted({r["subclass"] for r in SALES_OLAP_FACTS}),
            "sku": sorted({r["sku"] for r in SALES_OLAP_FACTS}),
            "region": sorted({r["region"] for r in SALES_OLAP_FACTS}),
        },
    }


def _total_revenue(rows: list[dict[str, Any]]) -> int:
    return sum(r["revenue"] for r in rows)


def _top_bottom(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        return {"top": None, "bottom": None}
    ordered = sorted(entries, key=lambda x: x["revenue"])
    return {"bottom": ordered[0], "top": ordered[-1]}


def _pct(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _prev_quarter(quarter: str | None) -> str | None:
    if not quarter:
        return None
    order = list(QUARTERS)
    if quarter not in order:
        return None
    idx = order.index(quarter)
    if idx == 0:
        return None
    return order[idx - 1]


def build_query_spec(
    quarter: str = "",
    subclass: str = "",
    sku: str = "",
    region: str = "",
    dimensions: str = "subclass",
    metrics: str = "revenue,units,avg_price",
    compare_to: str = "previous_quarter",
    rank_metric: str = "revenue",
    rank_order: str = "desc",
    limit: int = 5,
) -> dict[str, Any]:
    """
    Build and validate a deterministic QuerySpec for OLAP analysis.
    """
    normalized_quarter = _normalize_quarter(quarter)
    if quarter and not normalized_quarter:
        return {
            "error": f"Unsupported quarter '{quarter}'. Use Q1, Q2, Q3, or Q4.",
            "available_quarters": sorted(VALID_QUARTERS),
        }

    dims = _sanitize_dimensions(dimensions)
    mets = _sanitize_metrics(metrics)
    cleaned_subclass = subclass.strip() if subclass else None
    cleaned_sku = sku.strip().upper() if sku else None
    cleaned_region = region.strip().upper() if region else None

    rank_metric_clean = rank_metric.strip().lower() if rank_metric else "revenue"
    if rank_metric_clean not in VALID_METRICS:
        rank_metric_clean = "revenue"
    rank_order_clean = "asc" if rank_order.strip().lower() == "asc" else "desc"
    compare_to_clean = "previous_quarter" if compare_to.strip().lower() == "previous_quarter" else "none"
    try:
        safe_limit = int(limit or 5)
    except (TypeError, ValueError):
        safe_limit = 5
    safe_limit = min(max(safe_limit, 1), 25)

    query_spec = {
        "filters": {
            "quarter": normalized_quarter,
            "subclass": cleaned_subclass,
            "sku": cleaned_sku,
            "region": cleaned_region,
        },
        "dimensions": dims,
        "metrics": mets,
        "compare_to": compare_to_clean,
        "ranking": {
            "metric": rank_metric_clean,
            "order": rank_order_clean,
            "limit": safe_limit,
        },
    }
    return {"query_spec": query_spec}


def execute_query_spec(
    quarter: str = "",
    subclass: str = "",
    sku: str = "",
    region: str = "",
    dimensions: str = "subclass",
    metrics: str = "revenue,units,avg_price",
    compare_to: str = "previous_quarter",
    rank_metric: str = "revenue",
    rank_order: str = "desc",
    limit: int = 5,
) -> dict[str, Any]:
    """
    Execute a deterministic QuerySpec and return grouped rows + summary evidence.
    """
    spec_result = build_query_spec(
        quarter=quarter,
        subclass=subclass,
        sku=sku,
        region=region,
        dimensions=dimensions,
        metrics=metrics,
        compare_to=compare_to,
        rank_metric=rank_metric,
        rank_order=rank_order,
        limit=limit,
    )
    if "error" in spec_result:
        return spec_result

    query_spec = spec_result["query_spec"]
    filters = query_spec["filters"]
    dims = tuple(query_spec["dimensions"])
    mets = query_spec["metrics"]

    scope_rows = [
        r
        for r in SALES_OLAP_FACTS
        if (not filters["quarter"] or r["quarter"] == filters["quarter"])
    ]
    filtered_rows = [
        r
        for r in scope_rows
        if (not filters["subclass"] or r["subclass"].lower() == filters["subclass"].lower())
        and (not filters["sku"] or r["sku"] == filters["sku"])
        and (not filters["region"] or r["region"] == filters["region"])
    ]
    if not filtered_rows:
        return {"query_spec": query_spec, "message": "No matching rows for QuerySpec."}

    grouped = _aggregate(filtered_rows, dims)
    order_desc = query_spec["ranking"]["order"] == "desc"
    metric_for_sort = query_spec["ranking"]["metric"]
    sorted_grouped = sorted(grouped, key=lambda x: x.get(metric_for_sort, 0), reverse=order_desc)
    top_rows = sorted_grouped[: query_spec["ranking"]["limit"]]

    projected_rows: list[dict[str, Any]] = []
    for row in top_rows:
        projected = {"key": row["key"]}
        for metric in mets:
            projected[metric] = row.get(metric)
        projected_rows.append(projected)

    summary = {
        "rows": len(filtered_rows),
        "revenue": sum(r["revenue"] for r in filtered_rows),
        "units": sum(r["units"] for r in filtered_rows),
    }
    summary["avg_price"] = round(summary["revenue"] / max(summary["units"], 1), 2)

    comparison = None
    if query_spec["compare_to"] == "previous_quarter" and filters["quarter"]:
        prev_q = _prev_quarter(filters["quarter"])
        if prev_q:
            prev_rows = [
                r
                for r in SALES_OLAP_FACTS
                if r["quarter"] == prev_q
                and (not filters["subclass"] or r["subclass"].lower() == filters["subclass"].lower())
                and (not filters["sku"] or r["sku"] == filters["sku"])
                and (not filters["region"] or r["region"] == filters["region"])
            ]
            prev_rev = sum(r["revenue"] for r in prev_rows)
            prev_units = sum(r["units"] for r in prev_rows)
            prev_avg = round(prev_rev / max(prev_units, 1), 2)
            comparison = {
                "current_quarter": filters["quarter"],
                "previous_quarter": prev_q,
                "revenue_delta": summary["revenue"] - prev_rev,
                "revenue_delta_pct": _pct(summary["revenue"] - prev_rev, prev_rev),
                "units_delta": summary["units"] - prev_units,
                "units_delta_pct": _pct(summary["units"] - prev_units, prev_units),
                "avg_price_delta": round(summary["avg_price"] - prev_avg, 2),
                "avg_price_delta_pct": _pct(summary["avg_price"] - prev_avg, prev_avg),
            }

    return {
        "query_spec": query_spec,
        "summary": summary,
        "grouped_rows": projected_rows,
        "global_min_max_revenue": _min_max(_aggregate(scope_rows, ("subclass", "sku"))),
        "local_min_max_revenue": _min_max(grouped),
        "comparison": comparison,
    }


def build_analysis_plan(
    analysis_goal: str = "find_growth_and_risk_drivers",
    quarter: str = "",
    subclass: str = "",
    sku: str = "",
    region: str = "",
) -> dict[str, Any]:
    """
    Build an analyst-style AnalysisPlan with explicit drill and pivot rules.
    """
    normalized_quarter = _normalize_quarter(quarter)
    if quarter and not normalized_quarter:
        return {
            "error": f"Unsupported quarter '{quarter}'. Use Q1, Q2, Q3, or Q4.",
            "available_quarters": sorted(VALID_QUARTERS),
        }

    scope_filters = {
        "quarter": normalized_quarter,
        "subclass": subclass.strip() or None,
        "sku": sku.strip().upper() or None,
        "region": region.strip().upper() or None,
    }

    baseline_dims = "subclass"
    drill_dims = "sku"
    if scope_filters["subclass"] and not scope_filters["sku"]:
        baseline_dims = "sku"
        drill_dims = "region"
    if scope_filters["sku"]:
        baseline_dims = "region"
        drill_dims = "region"

    baseline_spec = build_query_spec(
        quarter=normalized_quarter or "",
        subclass=scope_filters["subclass"] or "",
        sku=scope_filters["sku"] or "",
        region=scope_filters["region"] or "",
        dimensions=baseline_dims,
        metrics="revenue,units,avg_price,rows",
        compare_to="previous_quarter",
        rank_metric="revenue",
        rank_order="desc",
        limit=6,
    ).get("query_spec")

    driver_drill_spec = build_query_spec(
        quarter=normalized_quarter or "",
        subclass=scope_filters["subclass"] or "",
        sku=scope_filters["sku"] or "",
        region=scope_filters["region"] or "",
        dimensions=drill_dims,
        metrics="revenue,units,avg_price",
        compare_to="previous_quarter",
        rank_metric="revenue",
        rank_order="desc",
        limit=6,
    ).get("query_spec")

    contrast_spec = build_query_spec(
        quarter=normalized_quarter or "",
        subclass="",
        sku="",
        region=scope_filters["region"] or "",
        dimensions="region",
        metrics="revenue,units,avg_price",
        compare_to="previous_quarter",
        rank_metric="revenue",
        rank_order="asc",
        limit=4,
    ).get("query_spec")

    return {
        "analysis_plan": {
            "analysis_goal": analysis_goal.strip() or "find_growth_and_risk_drivers",
            "scope_filters": scope_filters,
            "steps": [
                {
                    "step_id": "baseline",
                    "objective": "Establish KPI baseline and rank major contributors.",
                    "query_spec": baseline_spec,
                },
                {
                    "step_id": "driver_drill",
                    "objective": "Drill into the strongest contributor to isolate granular drivers.",
                    "query_spec": driver_drill_spec,
                },
                {
                    "step_id": "contrast_pivot",
                    "objective": "Pivot to weakest area for recovery-oriented contrast.",
                    "query_spec": contrast_spec,
                },
            ],
            "pivot_rules": [
                "If top contributor share < 30%, pivot from subclass to region concentration.",
                "If driver-vs-laggard gap < 10% of total revenue, pivot to SKU-level dispersion.",
                "If anomalies are present, prioritize anomaly branch before final recommendations.",
            ],
            "stop_rules": [
                "Stop when at least 4 quantified findings and 2 actionable recommendations are evidence-backed.",
                "Stop when both growth opportunity and downside risk are identified with explicit dimension keys.",
            ],
        }
    }


def investigate_sales_drilldown(
    quarter: str = "",
    subclass: str = "",
    region: str = "",
) -> dict[str, Any]:
    """
    Analyst-style drilldown:
    1) Baseline snapshot
    2) Identify strongest/weakest area
    3) Drill into driver area
    4) Cross-check another area for contrast
    """
    normalized_quarter = _normalize_quarter(quarter)
    if quarter and not normalized_quarter:
        return {
            "error": f"Unsupported quarter '{quarter}'. Use Q1, Q2, Q3, or Q4.",
            "available_quarters": sorted(VALID_QUARTERS),
        }

    base_rows = [
        r for r in SALES_OLAP_FACTS if (not normalized_quarter or r["quarter"] == normalized_quarter)
    ]
    if region:
        region_clean = region.strip().upper()
        base_rows = [r for r in base_rows if r["region"] == region_clean]
    if not base_rows:
        return {"message": "No matching data for requested scope."}

    overall_revenue = _total_revenue(base_rows)
    overall_units = sum(r["units"] for r in base_rows)
    overall_avg_price = round(overall_revenue / max(overall_units, 1), 2)
    prev_quarter = _prev_quarter(normalized_quarter)
    period_variance = None
    if normalized_quarter and prev_quarter:
        prev_rows = [r for r in SALES_OLAP_FACTS if r["quarter"] == prev_quarter]
        if region:
            prev_rows = [r for r in prev_rows if r["region"] == region.strip().upper()]
        prev_revenue = _total_revenue(prev_rows)
        prev_units = sum(r["units"] for r in prev_rows)
        prev_avg_price = round(prev_revenue / max(prev_units, 1), 2)
        period_variance = {
            "current_quarter": normalized_quarter,
            "previous_quarter": prev_quarter,
            "revenue_delta": overall_revenue - prev_revenue,
            "revenue_delta_pct": _pct(overall_revenue - prev_revenue, prev_revenue),
            "units_delta": overall_units - prev_units,
            "units_delta_pct": _pct(overall_units - prev_units, prev_units),
            "avg_price_delta": round(overall_avg_price - prev_avg_price, 2),
            "avg_price_delta_pct": _pct(overall_avg_price - prev_avg_price, prev_avg_price),
        }

    by_subclass = _aggregate(base_rows, ("subclass",))
    by_region = _aggregate(base_rows, ("region",))
    subclass_extrema = _top_bottom(by_subclass)
    region_extrema_all = _top_bottom(by_region)
    top_subclass = subclass_extrema["top"]["key"]["subclass"] if subclass_extrema["top"] else None
    bottom_subclass = subclass_extrema["bottom"]["key"]["subclass"] if subclass_extrema["bottom"] else None

    drill_subclass = subclass.strip() if subclass else top_subclass
    drill_rows = [r for r in base_rows if r["subclass"].lower() == drill_subclass.lower()] if drill_subclass else []
    by_sku_in_drill = _aggregate(drill_rows, ("sku",))
    sku_extrema = _top_bottom(by_sku_in_drill)

    by_region_in_drill = _aggregate(drill_rows, ("region",))
    region_extrema = _top_bottom(by_region_in_drill)

    # Follow-up area: contrast with weakest subclass at top-level to mimic analyst pivot.
    contrast_rows = [r for r in base_rows if r["subclass"] == bottom_subclass] if bottom_subclass else []
    contrast_by_region = _aggregate(contrast_rows, ("region",))
    contrast_extrema = _top_bottom(contrast_by_region)

    top_subclass_revenue = subclass_extrema["top"]["revenue"] if subclass_extrema["top"] else 0
    bottom_subclass_revenue = subclass_extrema["bottom"]["revenue"] if subclass_extrema["bottom"] else 0
    top_region_revenue = region_extrema_all["top"]["revenue"] if region_extrema_all["top"] else 0
    bottom_region_revenue = region_extrema_all["bottom"]["revenue"] if region_extrema_all["bottom"] else 0

    # Concentration and gap signals to drive analyst-quality insights.
    concentration_top2 = 0.0
    if by_subclass:
        ordered_subclass = sorted(by_subclass, key=lambda x: x["revenue"], reverse=True)
        concentration_top2 = _pct(
            sum(item["revenue"] for item in ordered_subclass[:2]),
            overall_revenue,
        )
    driver_gap = top_subclass_revenue - bottom_subclass_revenue
    regional_gap = top_region_revenue - bottom_region_revenue

    # Lightweight anomaly candidates by subclass+sku+region revenue.
    cell_entries = _aggregate(base_rows, ("subclass", "sku", "region"))
    ordered_cells = sorted(cell_entries, key=lambda x: x["revenue"])
    anomaly_candidates = []
    if ordered_cells:
        median_revenue = ordered_cells[len(ordered_cells) // 2]["revenue"]
        high_cut = median_revenue * 1.65
        low_cut = median_revenue * 0.62
        low_hits = [c for c in ordered_cells if c["revenue"] <= low_cut][:2]
        high_hits = [c for c in reversed(ordered_cells) if c["revenue"] >= high_cut][:2]
        anomaly_candidates = low_hits + high_hits

    return {
        "query_spec": build_query_spec(
            quarter=normalized_quarter or "",
            subclass=subclass,
            region=region,
            dimensions="subclass,sku,region",
            metrics="revenue,units,avg_price,rows",
            compare_to="previous_quarter",
            rank_metric="revenue",
            rank_order="desc",
            limit=8,
        ).get("query_spec"),
        "analysis_plan": build_analysis_plan(
            analysis_goal="find_growth_and_risk_drivers",
            quarter=normalized_quarter or "",
            subclass=subclass,
            region=region,
        ).get("analysis_plan"),
        "scope": {
            "quarter": normalized_quarter,
            "region": region.strip().upper() if region else None,
        },
        "baseline": {
            "revenue": overall_revenue,
            "units": overall_units,
            "avg_price": overall_avg_price,
            "subclass_count": len(by_subclass),
            "region_count": len(by_region),
            "top_subclass": subclass_extrema["top"],
            "bottom_subclass": subclass_extrema["bottom"],
            "top_region": region_extrema_all["top"],
            "bottom_region": region_extrema_all["bottom"],
            "period_variance_vs_previous_quarter": period_variance,
        },
        "insight_1_primary_driver": {
            "statement": (
                f"{top_subclass} is the primary revenue driver with "
                f"{_pct(top_subclass_revenue, overall_revenue)}% share."
                if top_subclass
                else "No primary driver available."
            ),
            "driver_subclass": top_subclass,
        },
        "drill_1_within_driver": {
            "subclass": drill_subclass,
            "sku_top": sku_extrema["top"],
            "sku_bottom": sku_extrema["bottom"],
            "region_top": region_extrema["top"],
            "region_bottom": region_extrema["bottom"],
        },
        "insight_2_contrast_area": {
            "statement": (
                f"{bottom_subclass} underperforms at {_pct(bottom_subclass_revenue, overall_revenue)}% share; "
                "investigate weakest region for recovery."
                if bottom_subclass
                else "No contrast area available."
            ),
            "contrast_subclass": bottom_subclass,
            "region_top": contrast_extrema["top"],
            "region_bottom": contrast_extrema["bottom"],
        },
        "insight_3_business_signals": {
            "concentration_top_2_subclass_pct": concentration_top2,
            "driver_vs_laggard_revenue_gap": driver_gap,
            "best_vs_worst_region_revenue_gap": regional_gap,
            "anomaly_candidates": anomaly_candidates,
        },
        "recommended_next_questions": [
            f"Drill from subclass '{top_subclass}' to SKU margin/price mix analysis.",
            f"Investigate region gap inside '{drill_subclass}' and test if pricing or volume drives variance.",
            f"Create turnaround plan for '{bottom_subclass}' in its weakest region.",
        ],
    }
