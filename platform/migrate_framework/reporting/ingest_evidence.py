"""Aggregate ingest evidence into reviewer-friendly summaries (no UI dependencies)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from migrate_framework.analysis.smell_catalog import enrich_landscape_smell

SOURCE_LABELS: dict[str, str] = {
    "metadata": "Landscape manifest, teams, smells, bounded contexts",
    "openapi": "REST API endpoints from OpenAPI specs",
    "sql-migration": "Database tables from SQL migration scripts",
    "trace": "Cross-service calls from trace fixtures",
    "maven": "Maven module / dependency graph",
    "spring-boot": "Spring Boot application configuration",
    "docker-compose": "Container wiring from compose files",
    "efcore": "Entity Framework data model",
    "csproj": ".NET project references",
    "aspnetcore": "ASP.NET Core host configuration",
}


def _items_as_dicts(items: list[Any]) -> list[dict[str, Any]]:
    return [item for item in items if isinstance(item, dict)]


def _merge_service_record(
    services: dict[str, dict[str, Any]],
    subject: str,
    attrs: dict[str, Any],
    source: str,
) -> None:
    """Merge service evidence; landscape manifest fields win over adapter stubs."""
    if subject not in services:
        services[subject] = {
            "service": subject,
            "port": None,
            "database": None,
            "tables": [],
            "team": None,
        }

    row = services[subject]
    prefer_source = source == "metadata"
    for key in ("port", "database", "team"):
        value = attrs.get(key)
        if value is None:
            continue
        if prefer_source or row.get(key) is None:
            row[key] = value

    new_tables = attrs.get("tables") or []
    if new_tables:
        merged = set(row.get("tables") or [])
        merged.update(new_tables)
        row["tables"] = sorted(merged)


def summarize_ingest_evidence(
    items: list[Any],
    *,
    adapters_used: str | None = None,
) -> dict[str, Any]:
    """Build structured ingest summary for artifacts and gate review."""
    evidence = _items_as_dicts(items)
    by_type = Counter(item.get("type") or "unknown" for item in evidence)
    by_source = Counter(item.get("source") or "unknown" for item in evidence)

    services: dict[str, dict[str, Any]] = {}
    smells: list[dict[str, Any]] = []
    raw_manifest_smells: list[tuple[str, str]] = []
    bounded_contexts: list[dict[str, Any]] = []
    http_deps: list[dict[str, str]] = []
    trace_calls: list[dict[str, str]] = []
    api_by_service: dict[str, list[str]] = defaultdict(list)
    db_tables: dict[str, list[str]] = defaultdict(list)

    for item in evidence:
        item_type = item.get("type") or ""
        subject = str(item.get("subject") or "")
        attrs = item.get("attributes") or {}
        source = str(item.get("source") or "")

        if item_type == "service":
            _merge_service_record(services, subject, attrs, source)
        elif item_type == "landscape_smell":
            smell_id = str(attrs.get("smell") or subject.split(":")[-1])
            service_id = str(attrs.get("service") or subject.split(":")[0])
            raw_manifest_smells.append((smell_id, service_id))
        elif item_type == "bounded_context":
            bounded_contexts.append(
                {
                    "context": subject,
                    "services": attrs.get("services") or [],
                }
            )
        elif item_type == "http_dependency" and "->" in subject:
            caller, callee = subject.split("->", 1)
            http_deps.append({"caller": caller, "callee": callee, "source": item.get("source")})
        elif item_type == "trace_span" and "->" in subject:
            caller, callee = subject.split("->", 1)
            trace_calls.append({"caller": caller, "callee": callee})
        elif item_type == "api_endpoint" and ":" in subject:
            service_name, endpoint = subject.split(":", 1)
            api_by_service[service_name].append(endpoint)
        elif item_type == "database_table" and "." in subject:
            left, right = subject.split(".", 1)
            table = attrs.get("table") or right
            item_source = item.get("source")
            if item_source in {"sql-migration", "metadata"}:
                db_tables[left].append(table)

    db_to_services: dict[str, list[str]] = defaultdict(set)
    for row in services.values():
        db = row.get("database")
        if db:
            db_to_services[str(db)].add(row["service"])

    db_sharing = {db: sorted(service_list) for db, service_list in db_to_services.items()}

    smells = [
        enrich_landscape_smell(
            smell_id,
            service_id,
            service_record=services.get(service_id),
            db_to_services=db_sharing,
        )
        for smell_id, service_id in raw_manifest_smells
    ]

    shared_databases = [
        {"database": db, "services": service_list, "service_count": len(service_list)}
        for db, service_list in sorted(db_sharing.items())
        if len(service_list) > 1
    ]

    service_rows = []
    for service_id in sorted(services.keys()):
        service_smell_rows = [s for s in smells if s["service"] == service_id]
        smell_titles = [
            s.get("summary_label") or s.get("title") or s.get("smell") for s in service_smell_rows
        ]
        api_paths = api_by_service.get(service_id, [])
        service_rows.append(
            {
                "service": service_id,
                "documented_smells": "; ".join(smell_titles) if smell_titles else "—",
                "smell_count": len(service_smell_rows),
                "smell_ids": [s.get("smell") for s in service_smell_rows],
                "smell_details": [
                    {
                        "smell": s.get("smell"),
                        "summary_label": s.get("summary_label"),
                        "database": s.get("database"),
                        "shared_with": s.get("shared_with") or [],
                    }
                    for s in service_smell_rows
                ],
                "api_endpoints": len(api_paths),
                "api_paths": api_paths,
                "outbound_http": sum(1 for d in http_deps if d["caller"] == service_id),
                "runtime_calls": sum(1 for t in trace_calls if t["caller"] == service_id),
            }
        )

    services_without_openapi = sorted(
        sid for sid in services if not api_by_service.get(sid)
    )

    confidences = [float(item.get("confidence", 1.0)) for item in evidence]
    low_confidence = [
        {
            "type": item.get("type"),
            "subject": item.get("subject"),
            "confidence": item.get("confidence"),
            "source": item.get("source"),
        }
        for item in evidence
        if float(item.get("confidence", 1.0)) < 0.8
    ]

    coverage_rows = [
        {
            "source": source,
            "label": SOURCE_LABELS.get(source, source),
            "count": count,
            "present": count > 0,
        }
        for source, count in by_source.most_common()
    ]

    readiness = {
        "services_discovered": len(services) > 0,
        "openapi_present": by_type.get("api_endpoint", 0) > 0,
        "schema_present": by_type.get("database_table", 0) > 0,
        "static_dependencies_present": by_type.get("http_dependency", 0) > 0,
        "runtime_traces_present": by_type.get("trace_span", 0) > 0,
        "landscape_smells_documented": by_type.get("landscape_smell", 0) > 0,
        "bounded_contexts_mapped": by_type.get("bounded_context", 0) > 0,
        "all_services_have_openapi": bool(services) and not services_without_openapi,
    }
    readiness_score = sum(1 for value in readiness.values() if value)

    return {
        "evidence_count": len(evidence),
        "adapters_used": adapters_used,
        "service_count": len(services),
        "bounded_context_count": len(bounded_contexts),
        "by_type": dict(by_type),
        "by_source": dict(by_source),
        "coverage": coverage_rows,
        "readiness": readiness,
        "readiness_score": f"{readiness_score}/{len(readiness)}",
        "shared_databases": shared_databases,
        "services_without_openapi": services_without_openapi,
        "low_confidence_count": len(low_confidence),
        "service_catalogue": service_rows,
        "landscape_smells": smells,
        "bounded_contexts": bounded_contexts,
        "http_dependencies": http_deps,
        "runtime_trace_calls": trace_calls,
        "database_tables": {db: sorted(tables) for db, tables in sorted(db_tables.items())},
        "api_endpoints_by_service": {
            service: endpoints[:12] for service, endpoints in sorted(api_by_service.items())
        },
        "api_endpoint_totals": {
            service: len(endpoints) for service, endpoints in sorted(api_by_service.items())
        },
    }
