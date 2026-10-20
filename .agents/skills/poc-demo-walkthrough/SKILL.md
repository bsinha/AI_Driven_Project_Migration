---
name: poc-demo-walkthrough
description: Step-by-step POC demo on EuroSA Bank sample landscape with approval gates. Use when running demo or presenting the migration framework.
---

# POC Demo Walkthrough

1. Run `.\scripts\run_pipeline.ps1` for the default live demo; it pauses for an operator decision at each required gate. Use `.\scripts\run_pipeline.ps1 -AutoApprove` only for an explicitly requested isolated demo.
2. Show pipeline progress in Streamlit: `streamlit run migrate_framework/ui/app.py`
3. Highlight: deterministic smells on 5 customer services (shared DB, co-change)
4. Show false cohesion: customer-preference vs risk-assessment (low co-change)
5. Demonstrate the **approve/reject/modify** decision flow on the recommend stage; do not pre-approve it.
6. Walk migration plan Phase 1 (Customer Management consolidation)
7. Show Stage 8 playbook — developer tasks, not auto-merge

See `docs/poc-demo-script.md` for full script.
