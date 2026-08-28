---
name: migration-playbook
description: Stage 8 developer playbook with manual migration tasks per phase. Use when guiding execution after plan approval.
---

# Migration Playbook (Stage 8)

1. Approve plan gate first
2. Run: `python -m migrate_framework.cli run --project-id <id> --stage playbook`
3. Output: task checklist per phase in `artifacts/playbook/`
4. Developer executes tasks manually — framework does **not** auto-merge code

Use Cursor alongside this skill for code assistance during manual migration.
