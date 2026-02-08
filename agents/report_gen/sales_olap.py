"""
Simple OLAP-style sales data store and query helpers.
"""

from typing import Any

# Flat fact-table shape keeps this simple and easy to filter/aggregate.
SALES_OLAP_FACTS: list[dict[str, Any]] = [
    # Q1
    {"quarter": "Q1", "region": "NA", "subclass": "Electronics", "sku": "ELEC-001", "units": 120, "revenue": 24000},
    {"quarter": "Q1", "region": "EU", "subclass": "Electronics", "sku": "ELEC-001", "units": 95, "revenue": 19500},
    {"quarter": "Q1", "region": "NA", "subclass": "Electronics", "sku": "ELEC-002", "units": 80, "revenue": 17600},
    {"quarter": "Q1", "region": "EU", "subclass": "Electronics", "sku": "ELEC-002", "units": 70, "revenue": 15400},
    {"quarter": "Q1", "region": "NA", "subclass": "Home", "sku": "HOME-001", "units": 150, "revenue": 22500},
    {"quarter": "Q1", "region": "EU", "subclass": "Home", "sku": "HOME-001", "units": 140, "revenue": 21000},
    {"quarter": "Q1", "region": "NA", "subclass": "Home", "sku": "HOME-002", "units": 110, "revenue": 14300},
    {"quarter": "Q1", "region": "EU", "subclass": "Home", "sku": "HOME-002", "units": 100, "revenue": 13000},
    # Q2
    {"quarter": "Q2", "region": "NA", "subclass": "Electronics", "sku": "ELEC-001", "units": 130, "revenue": 26650},
    {"quarter": "Q2", "region": "EU", "subclass": "Electronics", "sku": "ELEC-001", "units": 100, "revenue": 20500},
    {"quarter": "Q2", "region": "NA", "subclass": "Electronics", "sku": "ELEC-002", "units": 90, "revenue": 19800},
    {"quarter": "Q2", "region": "EU", "subclass": "Electronics", "sku": "ELEC-002", "units": 75, "revenue": 16500},
    {"quarter": "Q2", "region": "NA", "subclass": "Home", "sku": "HOME-001", "units": 165, "revenue": 24750},
    {"quarter": "Q2", "region": "EU", "subclass": "Home", "sku": "HOME-001", "units": 145, "revenue": 21750},
    {"quarter": "Q2", "region": "NA", "subclass": "Home", "sku": "HOME-002", "units": 120, "revenue": 15600},
    {"quarter": "Q2", "region": "EU", "subclass": "Home", "sku": "HOME-002", "units": 105, "revenue": 13650},
    # Q3
    {"quarter": "Q3", "region": "NA", "subclass": "Electronics", "sku": "ELEC-001", "units": 145, "revenue": 29725},
    {"quarter": "Q3", "region": "EU", "subclass": "Electronics", "sku": "ELEC-001", "units": 110, "revenue": 22550},
    {"quarter": "Q3", "region": "NA", "subclass": "Electronics", "sku": "ELEC-002", "units": 95, "revenue": 20900},
    {"quarter": "Q3", "region": "EU", "subclass": "Electronics", "sku": "ELEC-002", "units": 82, "revenue": 18040},
    {"quarter": "Q3", "region": "NA", "subclass": "Home", "sku": "HOME-001", "units": 172, "revenue": 25800},
    {"quarter": "Q3", "region": "EU", "subclass": "Home", "sku": "HOME-001", "units": 152, "revenue": 22800},
    {"quarter": "Q3", "region": "NA", "subclass": "Home", "sku": "HOME-002", "units": 128, "revenue": 16640},
    {"quarter": "Q3", "region": "EU", "subclass": "Home", "sku": "HOME-002", "units": 108, "revenue": 14040},
    # Q4
    {"quarter": "Q4", "region": "NA", "subclass": "Electronics", "sku": "ELEC-001", "units": 160, "revenue": 32800},
    {"quarter": "Q4", "region": "EU", "subclass": "Electronics", "sku": "ELEC-001", "units": 120, "revenue": 24600},
    {"quarter": "Q4", "region": "NA", "subclass": "Electronics", "sku": "ELEC-002", "units": 102, "revenue": 22440},
    {"quarter": "Q4", "region": "EU", "subclass": "Electronics", "sku": "ELEC-002", "units": 88, "revenue": 19360},
    {"quarter": "Q4", "region": "NA", "subclass": "Home", "sku": "HOME-001", "units": 185, "revenue": 27750},
    {"quarter": "Q4", "region": "EU", "subclass": "Home", "sku": "HOME-001", "units": 160, "revenue": 24000},
    {"quarter": "Q4", "region": "NA", "subclass": "Home", "sku": "HOME-002", "units": 138, "revenue": 17940},
    {"quarter": "Q4", "region": "EU", "subclass": "Home", "sku": "HOME-002", "units": 115, "revenue": 14950},
]

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
    subclass_extrema = _top_bottom(by_subclass)
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
            "top_subclass": subclass_extrema["top"],
            "bottom_subclass": subclass_extrema["bottom"],
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
        "recommended_next_questions": [
            f"Drill from subclass '{top_subclass}' to SKU margin/price mix analysis.",
            f"Investigate region gap inside '{drill_subclass}' and test if pricing or volume drives variance.",
            f"Create turnaround plan for '{bottom_subclass}' in its weakest region.",
        ],
    }
