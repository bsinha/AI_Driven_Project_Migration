---
name: migration-playbook
description: Stage 8 developer playbook with manual migration tasks per phase. Use when guiding execution after plan approval.
---

# Migration Playbook (Stage 8)

1. Approve plan gate first
2. Run: `python -m migrate_framework.cli run --project-id <id> --stage playbook`
3. Output: task checklist per phase in `artifacts/playbook/`
4. Developer executes tasks manually — framework does **not** auto-merge code

## Assisted execution (diff review)

After playbook generation, use the Streamlit dashboard **Assisted task execution** section:

1. Filter tasks by phase (e.g. Phase 1 — Customer Management)
2. Click **Generate assistance** on a task
3. Review unified diffs for each proposed file
4. Check/uncheck files to approve
5. Click **Apply approved files** — only then are changes written under `target-contexts/`
6. Mark task **complete** after validation (tests, PR review)

Supported assisted task patterns:

- Scaffold target bounded context
- Anti-corruption layer stubs
- Schema migration script drafts
- Contract test placeholders
- Aggregate root documentation
- Unified API OpenAPI draft

Other tasks return manual guidance only.

Use Cursor alongside this skill for deeper code assistance after applying scaffolds.
