---
name: generate-adr
description: Generates Architecture Decision Records with evidence bullets for bounded context recommendations. Use at pipeline stage 6 (recommend).
---

# Generate ADR

1. Complete hypothesize stage
2. Run: `python -m migrate_framework.cli run --project-id <id> --stage recommend`
3. Output: `artifacts/recommend/adrs.yaml`
4. Human gate required before plan stage

Each ADR must include: context, decision, consequences, affected services, confidence, evidence references.

See `docs/adr-appendix.md` for sample output format.
