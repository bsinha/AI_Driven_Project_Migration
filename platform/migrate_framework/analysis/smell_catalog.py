"""Architecture smell definitions for human-readable review in ingest and diagnose."""

from __future__ import annotations

from typing import Any

SmellDefinition = dict[str, str]

SMELL_CATALOG: dict[str, SmellDefinition] = {
    "shared_database": {
        "title": "Shared database",
        "severity": "high",
        "description": (
            "Multiple microservices read and write the same database schema. "
            "Data ownership is unclear and schema changes require coordinated releases."
        ),
        "migration_impact": (
            "Blocks clean bounded-context cutover until each service owns its data store "
            "or a deliberate shared-data strategy is approved."
        ),
        "what_to_verify": (
            "List all services on the same DB, table ownership, and cross-service FKs."
        ),
    },
    "granular_decomposition": {
        "title": "Granular decomposition",
        "severity": "high",
        "description": (
            "Capabilities that belong to one business context are split across many "
            "fine-grained services (often sharing data and synchronous calls)."
        ),
        "migration_impact": (
            "Consolidation into a bounded context is likely; ingest evidence should show "
            "clustered APIs, smells, and shared schema for the same squad."
        ),
        "what_to_verify": (
            "Whether services can be merged without losing independent scaling needs."
        ),
    },
    "cross_service_fk": {
        "title": "Cross-service foreign keys",
        "severity": "high",
        "description": (
            "Database relationships span service boundaries, coupling schemas across "
            "deployment units."
        ),
        "migration_impact": (
            "Schema split requires FK removal, reference-by-ID, or eventual consistency."
        ),
        "what_to_verify": (
            "FK targets, read patterns, and whether IDs are stable across contexts."
        ),
    },
    "sync_rest_chain": {
        "title": "Synchronous REST chain",
        "severity": "medium",
        "description": (
            "Runtime or declared HTTP call chains where one user action triggers multiple "
            "sequential service calls."
        ),
        "migration_impact": (
            "Increases latency and failure blast radius; migration may need events, sagas, "
            "or orchestration."
        ),
        "what_to_verify": (
            "Chain length, critical path, timeouts, and which calls are on the hot path."
        ),
    },
    "false_cohesion_candidate": {
        "title": "False cohesion candidate",
        "severity": "medium",
        "description": (
            "Service appears cohesive by name or team but shares a database or depends "
            "heavily on sibling services for core workflows."
        ),
        "migration_impact": (
            "May stay separate operationally but should not be treated as an independent "
            "bounded context without evidence."
        ),
        "what_to_verify": (
            "Whether the service has autonomous data and release lifecycle."
        ),
    },
    "lifecycle_split": {
        "title": "Lifecycle split",
        "severity": "medium",
        "description": (
            "Different lifecycle states of the same aggregate (e.g. status, history) are "
            "implemented as separate services."
        ),
        "migration_impact": (
            "Often merged into one aggregate root or coordinated via domain events in TO-BE."
        ),
        "what_to_verify": (
            "State transitions, who owns the aggregate root, and consistency requirements."
        ),
    },
    "distributed_transaction_path": {
        "title": "Distributed transaction path",
        "severity": "high",
        "description": (
            "A business operation spans multiple services and databases with implicit "
            "all-or-nothing expectations."
        ),
        "migration_impact": (
            "Requires explicit consistency model: saga, outbox, or accepted eventual consistency."
        ),
        "what_to_verify": (
            "Failure modes, compensations, and whether strong consistency is truly required."
        ),
    },
    "sync_called_by_payment": {
        "title": "Payment sync dependency",
        "severity": "medium",
        "description": (
            "A supporting service is invoked synchronously from the payment flow, putting "
            "it on the critical payment path."
        ),
        "migration_impact": (
            "Payment cutover risks if this dependency is slow or unavailable; consider async "
            "or cached reads."
        ),
        "what_to_verify": (
            "Call frequency, latency SLA, and fallback behaviour during payment execution."
        ),
    },
    "false_cohesion": {
        "title": "False cohesion",
        "severity": "medium",
        "description": (
            "Service bundles concerns that belong to different business capabilities "
            "(e.g. risk logic mixed with customer naming)."
        ),
        "migration_impact": (
            "May need split or ACL when aligning to target bounded contexts."
        ),
        "what_to_verify": (
            "API surface, data owned, and which target context should own each capability."
        ),
    },
    "customer_in_api_name": {
        "title": "Customer leakage in API",
        "severity": "low",
        "description": (
            "Service or API names expose customer-domain concepts while the service sits "
            "outside the customer bounded context."
        ),
        "migration_impact": (
            "Signals boundary smell; TO-BE APIs may rename or move behind an anti-corruption layer."
        ),
        "what_to_verify": (
            "Whether callers treat this as customer data access or a generic capability."
        ),
    },
}

_DEFAULT_SMELL: SmellDefinition = {
    "title": "Documented smell",
    "severity": "medium",
    "description": "Architecture smell recorded in the landscape manifest without a catalog entry.",
    "migration_impact": "Review with domain SMEs before approving ingest.",
    "what_to_verify": "Why the smell was tagged and what evidence supports it.",
}


def smell_definition(smell_id: str) -> SmellDefinition:
    return SMELL_CATALOG.get(smell_id, {**_DEFAULT_SMELL, "title": smell_id.replace("_", " ").title()})


def smell_summary_label(
    smell_id: str,
    service: str,
    *,
    service_record: dict[str, Any] | None = None,
    db_to_services: dict[str, list[str]] | None = None,
) -> str:
    """One-line smell label for tables, including shared-database detail when known."""
    meta = smell_definition(smell_id)
    if smell_id == "shared_database" and service_record:
        database = service_record.get("database")
        if database:
            peers = []
            if db_to_services and database in db_to_services:
                peers = [s for s in db_to_services[database] if s != service]
            if peers:
                return (
                    f"Shared database — `{database}` shared with "
                    f"{', '.join(peers)}"
                )
            return f"Shared database — `{database}`"
    return meta["title"]


def enrich_landscape_smell(
    smell_id: str,
    service: str,
    *,
    service_record: dict[str, Any] | None = None,
    db_to_services: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Build a reviewer-oriented smell row with catalog text and service context."""
    meta = smell_definition(smell_id)
    context_notes: list[str] = []
    database_name: str | None = None
    shared_with: list[str] = []

    if smell_id == "shared_database" and service_record:
        database = service_record.get("database")
        if database:
            database_name = str(database)
            context_notes.append(f"Uses database `{database}`.")
            if db_to_services and database in db_to_services:
                peers = [s for s in db_to_services[database] if s != service]
                shared_with = peers
                if peers:
                    context_notes.append(
                        f"Shared with {len(peers)} other service(s): {', '.join(peers)}."
                    )

    if service_record:
        team = service_record.get("team")
        if team:
            context_notes.append(f"Team: {team}.")

    context = " ".join(context_notes)
    summary_label = smell_summary_label(
        smell_id,
        service,
        service_record=service_record,
        db_to_services=db_to_services,
    )

    return {
        "service": service,
        "smell": smell_id,
        "title": meta["title"],
        "summary_label": summary_label,
        "severity": meta["severity"],
        "description": meta["description"],
        "migration_impact": meta["migration_impact"],
        "what_to_verify": meta["what_to_verify"],
        "context": context or "—",
        "database": database_name,
        "shared_with": shared_with,
    }
