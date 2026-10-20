# MATE
## Modernization & Architecture Transformation Engine

Evidence-led architecture modernization POC — an 8-stage gated pipeline demonstrated on EuroSA Bank (Java/Spring Boot granular services).

## Quick start

```powershell
# Platform
cd platform
pip install -e ".[dev]"

# Full pipeline on sample bank (manual approval is the default)
..\scripts\run_pipeline.ps1

# Explicit isolated demo only
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
| `AGENTS.md` and `.agents/skills/` | Codex project guidance and repeatable workflows |

## Pipeline

Discover → Ingest → **[gate]** → Graph → Diagnose → **[gate]** → Hypothesize → **[gate]** → Recommend → **[gate]** → Plan → **[gate]** → Playbook

**Never auto-merges services.** `discover`, `ingest`, `graph`, and `diagnose` are deterministic. Required gates are `ingest`, `diagnose`, `hypothesize`, `recommend`, and `plan`; each is reviewed after its stage completes and before the next stage runs. Recommendation and plan remain explicit human decision points.

## Documentation

- [Logical architecture (MATE v2)](docs/mate-logical-architecture.md) — platform overview, V&V loop, POC vs roadmap
- [Problem statement](docs/problem-statement.md)
- [Framework methodology](docs/framework-methodology.md)
- [Operating model](docs/operating-model.md) — deterministic analysis, pattern-constrained AI, iteration, customer story
- [Complexity matrix](docs/migration-complexity-matrix.md) — exception scenarios & POC coverage
- [POC demo script](docs/poc-demo-script.md)

## Environment

Copy `platform/.env.example` to `platform/.env` and set `OPENAI_API_KEY` (optional — mock mode without key).
