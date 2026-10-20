---
name: bounded-context-analysis
description: Runs diagnose through recommend stages with evidence-backed bounded context discovery. Use for architecture health assessment, smell detection, or AI hypotheses.
---

# Bounded Context Analysis

1. Confirm the existing project and status before running a stage.
2. Complete `discover`, `ingest`, and `graph`, approving the required `ingest` gate after ingestion and before graph.
3. Diagnose (deterministic): `python -m migrate_framework.cli run --project-id <id> --stage diagnose` — coupling, smells, and health report. Approve the `diagnose` gate before hypothesize.
4. Hypothesize: `python -m migrate_framework.cli run --project-id <id> --stage hypothesize` — 2–4 candidate contexts (OpenAI or mock). Approve the `hypothesize` gate before recommend.
5. Recommend: `python -m migrate_framework.cli run --project-id <id> --stage recommend` — ADRs and target architecture. Review and approve the `recommend` gate before plan with `approve --stage recommend`.

Never skip diagnose — LLM receives pre-computed metrics only.
