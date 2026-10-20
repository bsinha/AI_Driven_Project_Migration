---
name: generate-migration-plan
description: Generates a phased migration plan with sequencing, risks, and compatibility layers at the plan stage.
---

# Generate Migration Plan

1. Complete recommend stage and approve its required gate.
2. Run: `python -m migrate_framework.cli run --project-id <id> --stage plan`
3. Review `platform/projects/<id>/artifacts/plan/migration-plan.json`.
4. Approve the completed plan gate explicitly, or reject/waive it with documented reasons: `python -m migrate_framework.cli approve --project-id <id> --stage plan --by <operator>`.

Phases typically: Customer → Account → Payments → Risk/Compliance
