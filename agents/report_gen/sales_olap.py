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
