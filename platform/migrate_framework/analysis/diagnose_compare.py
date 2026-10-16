"""Compare diagnose runs for phase validation."""

from __future__ import annotations

from typing import Any


def _smell_types(smells: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for smell in smells:
        key = smell.get("type", "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _filter_smells_by_services(smells: list[dict[str, Any]], services: set[str] | None) -> list[dict[str, Any]]:
    if not services:
        return smells
    filtered = []
    for smell in smells:
        smell_services = set(smell.get("services") or smell.get("affected_services") or [])
        if not smell_services or smell_services & services:
            filtered.append(smell)
    return filtered


def compare_diagnose(
    baseline: dict[str, Any],
    current: dict[str, Any],
    scope_services: list[str] | None = None,
) -> dict[str, Any]:
    """Metric delta between two diagnose payloads, optionally scoped to services."""
    service_set = set(scope_services) if scope_services else None
    base_smells = _filter_smells_by_services(baseline.get("smells", []), service_set)
    curr_smells = _filter_smells_by_services(current.get("smells", []), service_set)

    base_open = [s for s in base_smells if s.get("governance_status", "open") == "open"]
    curr_open = [s for s in curr_smells if s.get("governance_status", "open") == "open"]

    base_metrics = baseline.get("metrics", {})
    curr_metrics = current.get("metrics", {})

    smell_delta = len(curr_open) - len(base_open)
    improved = smell_delta < 0

    return {
        "baseline_smell_count": len(base_open),
        "current_smell_count": len(curr_open),
        "smell_delta": smell_delta,
        "improved": improved,
        "baseline_by_type": _smell_types(base_open),
        "current_by_type": _smell_types(curr_open),
        "service_count_baseline": baseline.get("service_count", base_metrics.get("service_count")),
        "service_count_current": current.get("service_count", curr_metrics.get("service_count")),
        "scope_services": sorted(service_set) if service_set else [],
    }
