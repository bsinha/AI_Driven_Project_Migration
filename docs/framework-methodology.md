# Framework Methodology — 8-Stage Pipeline

See also: [Operating model](operating-model.md) (iteration, deterministic vs AI, rejection paths) · [Complexity matrix](migration-complexity-matrix.md) (exception scenarios).

## Stages

| # | Stage | Actor | Output |
|---|-------|-------|--------|
| 1 | Discover | Framework | Service inventory, tech stack profile |
| 2 | Collect Evidence | Adapters | Normalized evidence bundle |
| 3 | Model | Graph builder | Architecture knowledge graph |
| 4 | Diagnose | Metrics engine | Health report, smells |
| 5 | Hypothesize | AI | 2–4 candidate bounded contexts |
| 6 | Recommend | AI | Target architecture, ADRs |
| 7 | Plan | Framework + AI | Phased migration plan |
| 8 | Guide | Developer + framework | Playbook tasks |

## Human gates

- **After Recommend (Stage 6):** Approve / reject / modify target architecture
- **After Plan (Stage 7):** Approve migration plan before playbook

Rejection = withhold approval and re-run upstream stages (e.g. re-hypothesize, edit ADRs, re-plan). See [operating model — re-entry paths](operating-model.md#re-entry-and-rejection-paths).

## Iteration

- **Within a phase:** rejected hypothesis → refine evidence → re-hypothesize → recommend again
- **Across phases:** complete Phase N playbook → validate (re-diagnose) → Phase N+1 pipeline run
- **Feedback loop:** validation failure → re-diagnose or re-plan before next cutover
- **Scoped pilot:** per-ADR approve / defer via `item_decisions`; deferred ADRs remain AS-IS until a later wave
- **Smell exceptions:** per-smell accept / defer via `smell_decisions`; accepted smells stay visible in diagnose but are excluded from planning
- **Phase snapshots:** `phase_snapshots` metadata stores eight-stage metrics per program phase for readiness scoring

CLI: `scope-decide`, `scope-pilot`, `scope-decide-batch`, `smell-decide`, `smell-decide-batch`, `phase-set-contexts`, `phase-close`.

**Streamlit UI parity:** Governance → Pilot scope wizard (batch ADRs); Phases → context assignment, phase close, batch smell decisions; per-item controls remain for fine-grained edits.

## Onboarding a new codebase

```bash
cd platform
pip install -e ".[dev]"
python -m migrate_framework.cli init --name "MyBank" --source /path/to/code
python -m migrate_framework.cli run --project-id <id> --stage discover --through playbook
```

## Technology support

- **Java / Spring Boot:** Full adapters (POC)
- **.NET / ASP.NET Core:** Adapter stubs registered; implement for Phase 2
- **Shared:** OpenAPI, SQL migrations, Docker Compose, synthetic metadata

Only ingestion adapters change per stack; pipeline core is unchanged.
