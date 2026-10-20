---
name: generate-adr
description: Generates Architecture Decision Records with evidence bullets for bounded context recommendations at the recommend stage.
---

# Generate ADR

1. Complete hypothesize stage and clear its required gate.
2. Run: `python -m migrate_framework.cli run --project-id <id> --stage recommend`
3. Output: `platform/projects/<id>/artifacts/recommend/adrs.yaml`
4. Review ADRs and make any item-level scope decisions required by the project.
5. Human gate required after recommend and before plan: `python -m migrate_framework.cli approve --project-id <id> --stage recommend --by <operator>`.

Each ADR must include: context, decision, consequences, affected services, confidence, evidence references.

See `docs/adr-appendix.md` for sample output format.
