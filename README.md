# MATE
## Modernization & Architecture Transformation Engine

Evidence-led architecture modernization POC — an 8-stage gated pipeline demonstrated on EuroSA Bank (Java/Spring Boot granular services).

## Quick start

```powershell
# Platform
cd platform
pip install -e ".[dev]"

# Full pipeline on sample bank
..\scripts\run_pipeline.ps1 -AutoApprove

# API + Dashboard
uvicorn migrate_framework.api.main:app --reload --port 8080
streamlit run migrate_framework/ui/app.py
```

## Repository layout

| Path                             | Purpose                                          |
| -------------------------------- | ------------------------------------------------ |
| `platform/migrate_framework/`    | Python framework (pipeline, adapters, graph, AI) |
| `sample-bank/granular-services/` | 16 intentional granular Java services            |
| `metadata/`                      | Synthetic traces, co-change, teams               |
| `docs/`                          | Problem statement, methodology, demo script      |
| `.cursor/rules/`                 | Cursor AI guidance                               |

## Pipeline

Discover → Evidence → Model → Diagnose → Hypothesize → Recommend → **[gate]** → Plan → **[gate]** → Guide

**Never auto-merges services.** Stages 1–4 are deterministic; human approval is required at the architecture recommendation and migration plan gates.

## Documentation

- [Problem statement](docs/problem-statement.md)
- [Framework methodology](docs/framework-methodology.md)
- [Operating model](docs/operating-model.md) — deterministic analysis, pattern-constrained AI, iteration, customer story
- [Complexity matrix](docs/migration-complexity-matrix.md) — exception scenarios & POC coverage
- [POC demo script](docs/poc-demo-script.md)

## Environment

Copy `platform/.env.example` to `platform/.env` and set `OPENAI_API_KEY` (optional — mock mode without key).
