---
name: generate-migration-plan
description: Generates phased migration plan with sequencing, risks, and compatibility layers. Use at pipeline stage 7 (plan).
---

# Generate Migration Plan

1. Complete recommend stage and approve gate
2. Run: `python -m migrate_framework.cli run --project-id <id> --stage plan`
3. Review `artifacts/plan/migration-plan.json`
4. Approve: `python -m migrate_framework.cli approve --project-id <id> --stage plan`

Phases typically: Customer → Account → Payments → Risk/Compliance
