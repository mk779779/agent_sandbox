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
