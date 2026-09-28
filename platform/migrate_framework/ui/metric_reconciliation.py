"""Dashboard metric definitions and reconciliation messages (deterministic, no Streamlit)."""

from __future__ import annotations

from typing import Any


def discovered_service_count(ingest: dict[str, Any]) -> int:
    return int(ingest.get("service_count") or 0)


def catalogue_service_ids(ingest: dict[str, Any]) -> set[str]:
    return {str(row["service"]) for row in (ingest.get("service_catalogue") or []) if row.get("service")}


def context_service_ids(bounded_contexts: list[dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    for ctx in bounded_contexts:
        for svc in ctx.get("services") or []:
            seen.add(str(svc))
    return seen


def services_not_in_bounded_contexts(
    ingest: dict[str, Any],
    bounded_contexts: list[dict[str, Any]],
) -> list[str]:
    """Services in ingest catalogue but not listed on any bounded_context evidence row."""
    catalogue = catalogue_service_ids(ingest)
    in_context = context_service_ids(bounded_contexts)
    if catalogue:
        return sorted(catalogue - in_context)
    discovered = discovered_service_count(ingest)
    if discovered and len(in_context) < discovered:
        return []
    return sorted(catalogue - in_context)


def shared_database_cluster_count(ingest: dict[str, Any]) -> int:
    return len(ingest.get("shared_databases") or [])


def services_on_shared_databases(ingest: dict[str, Any]) -> set[str]:
    affected: set[str] = set()
    for row in ingest.get("shared_databases") or []:
        for svc in row.get("services") or []:
            affected.add(str(svc))
    return affected


def manifest_smell_rows(ingest: dict[str, Any]) -> list[dict[str, Any]]:
    return list(ingest.get("landscape_smells") or [])


def open_diagnosis_smell_rows(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        s
        for s in (diagnosis.get("smells") or [])
        if s.get("governance_status", "open") == "open"
    ]


def service_reconciliation_message(
    ingest: dict[str, Any],
    bounded_contexts: list[dict[str, Any]],
) -> str | None:
    discovered = discovered_service_count(ingest)
    in_context = len(context_service_ids(bounded_contexts))
    unmapped = services_not_in_bounded_contexts(ingest, bounded_contexts)
    if discovered == in_context and not unmapped:
        return None
    parts = [
        f"**{discovered}** services discovered (ingest evidence); "
        f"**{in_context}** assigned to bounded contexts (manifest mapping)."
    ]
    if unmapped:
        preview = ", ".join(f"`{s}`" for s in unmapped[:5])
        suffix = f" (+{len(unmapped) - 5} more)" if len(unmapped) > 5 else ""
        parts.append(f"Not in any bounded context: {preview}{suffix}. Check manifest **target_bounded_contexts**.")
    elif discovered != in_context:
        parts.append("Counts differ — refresh **ingest** or compare Pipeline → Ingest tables.")
    return " ".join(parts)


def smell_reconciliation_message(
    ingest: dict[str, Any],
    diagnosis: dict[str, Any],
) -> str | None:
    manifest_n = len(manifest_smell_rows(ingest))
    open_n = len(open_diagnosis_smell_rows(diagnosis))
    if not diagnosis.get("smells"):
        return None
    if manifest_n == open_n:
        return None
    return (
        f"**{manifest_n}** manifest smell tags (landscape documentation) vs "
        f"**{open_n}** open **diagnosis** findings (includes shared DB, sync chains, and re-listed manifest items). "
        "Use the smell source toggle above the chart or see Pipeline → **diagnose**."
    )
