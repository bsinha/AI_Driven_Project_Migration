---
name: run-pipeline-stage
description: Executes one stage of the eight-stage migration pipeline after inspecting project state and honoring approval gates.
---

# Run Pipeline Stage

1. Inspect existing state first from `platform/`: `python -m migrate_framework.cli list`, then `python -m migrate_framework.cli status --project-id <id>` for the selected project.
2. Do not install dependencies, initialize a project, or create a duplicate project as an implicit part of this skill. If the project does not exist, stop and ask the operator to initialize it explicitly with the repository's documented environment and source paths.
3. Confirm the immediately preceding stage is completed. Run only the requested stage: `python -m migrate_framework.cli run --project-id <id> --stage <stage>`.
4. Review the generated artifacts under `platform/projects/<id>/artifacts/<stage>/` and the project status.
5. For required gates, obtain an explicit operator decision after the stage completes. Approve with `python -m migrate_framework.cli approve --project-id <id> --stage <stage> --by <operator>` or use `reject`/`waive` with the required reason arguments. Never pre-approve a stage or use `--auto-approve` unless the user explicitly requests an isolated demo.
6. Continue to the next stage only after the prior stage is completed and its required gate is approved or waived.

Stages: `discover`, `ingest`, `graph`, `diagnose`, `hypothesize`, `recommend`, `plan`, `playbook`.

Required gates: `ingest`, `diagnose`, `hypothesize`, `recommend`, `plan`. Non-required gates: `discover`, `graph`, `playbook`.
