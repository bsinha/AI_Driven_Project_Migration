---
name: run-pipeline-stage
description: Executes one stage of the 8-stage migration pipeline with gate enforcement. Use when running discover, evidence, diagnose, hypothesize, recommend, plan, or guide stages.
---

# Run Pipeline Stage

1. `cd platform && pip install -e ".[dev]"`
2. Init: `python -m migrate_framework.cli init --name "EuroSA" --source ../sample-bank --landscape ../sample-bank/landscape-manifest.yaml`
3. Run stage: `python -m migrate_framework.cli run --project-id <id> --stage <stage>`
4. Approve gates: `python -m migrate_framework.cli approve --project-id <id> --gate recommend`
5. Artifacts: `platform/projects/{id}/artifacts/`

Stages: discover, ingest, graph, diagnose, hypothesize, recommend, plan, playbook
