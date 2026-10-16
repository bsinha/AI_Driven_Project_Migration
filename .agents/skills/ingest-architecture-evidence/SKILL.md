---
name: ingest-architecture-evidence
description: Runs ingestion adapters to collect evidence from a microservice codebase. Use for stage 2 evidence collection, knowledge graph input, or scanning services.
---

# Ingest Architecture Evidence

1. Ensure project initialized with `--source` pointing at codebase root
2. Run: `python -m migrate_framework.cli run --project-id <id> --stage ingest`
3. Adapters auto-selected from tech stack profile (Java Spring Boot, .NET stub, shared OpenAPI/SQL/trace)
4. Output: `artifacts/ingest/evidence.json`

Supplement with `metadata/` synthetic traces, co-change, teams if not in repo.
