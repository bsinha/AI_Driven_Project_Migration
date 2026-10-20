---
name: ingest-architecture-evidence
description: Runs ingestion adapters to collect evidence from a microservice codebase. Use for stage 2 evidence collection, knowledge graph input, or scanning services.
---

# Ingest Architecture Evidence

1. Inspect `python -m migrate_framework.cli list` and `status` first. Use an existing project initialized with `--source` pointing at the codebase root; do not initialize a duplicate project implicitly.
2. Run: `python -m migrate_framework.cli run --project-id <id> --stage ingest`
3. Adapters are auto-selected from the tech stack profile (Java Spring Boot, .NET stub, shared OpenAPI/SQL/trace).
4. Output: `platform/projects/<id>/artifacts/ingest/evidence.json`.
5. Review the evidence and approve the required ingest gate before running graph.

Supplement with `metadata/` synthetic traces, co-change, teams if not in repo.
