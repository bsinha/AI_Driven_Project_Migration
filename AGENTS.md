# Agent Orchestration

## Project standards

- The migration framework core stays technology-agnostic; stack-specific logic belongs in ingestion adapters.
- The pipeline stages are `discover` → `ingest` → `graph` → `diagnose` → `hypothesize` → `recommend` → `plan` → `playbook`.
- `discover`, `ingest`, `graph`, and `diagnose` are deterministic; AI stages must use evidence-backed inputs and outputs.
- The required approval gates are `ingest`, `diagnose`, `hypothesize`, `recommend`, and `plan`. `discover`, `graph`, and `playbook` have non-required gates.
- A required gate is reviewed after its stage completes and must be approved or formally waived before the next stage can run. Recommendation and plan require explicit human approval; approvals must never be inferred or pre-applied.
- Never auto-merge services. The playbook supports developer-guided execution only.

### `platform/`

- Keep adapters technology-neutral at the pipeline boundary by emitting `EvidenceItem` values.
- Use NetworkX for the architecture graph, FastAPI for the API, and Streamlit for the UI.
- OpenAI is optional; preserve mock behavior when `OPENAI_API_KEY` is unset.
- Recommendations must cite metrics, traces, co-change, or data ownership. ADRs explain why services belong together, why they should not remain separate, and the risks. Flag false cohesion where names overlap but data or traffic does not.

### `sample-bank/`

- This is an intentionally over-decomposed Spring Boot 3 / Java 17 POC. Preserve EuroSA Bank, ZAR, and FICA context.
- Each granular service should retain its `pom.xml`, `application.yml`, and `openapi.yaml`.
- Do not refactor toward clean architecture or remove intentional smells: shared customer databases, synchronous REST chains, cross-service foreign keys, over-splitting, and false cohesion are detection targets.

## Landscape work (`sample-bank/`)

- Inspect and map granular-services before editing, using the available Codex workspace tools or equivalent repository inspection.
- Use `over-split-microservice` skill only for POC setup
- **Never** refactor toward clean architecture — smells are intentional

## Analysis work (`platform/`)

- Use `bounded-context-analysis` skill before optional OpenAI calls.
- Inspect the ingestion → graph → analysis flow before making changes.
- Use code-review tooling only when the user explicitly requests code review.

## Parallel patterns

- Parallelize independent repository inspections when useful (for example, Java scanning, OpenAPI parsing, and metadata loading).
- Keep ADR drafting and architecture-document updates independently reviewable.

## Pipeline order

discover → ingest → [gate] → graph → diagnose → [gate] → hypothesize → [gate] → recommend → [gate] → plan → [gate] → playbook

The gate belongs to the completed stage. `PipelineOrchestrator.can_run()` checks that the immediately preceding stage completed and that its required gate is cleared before allowing the next stage. `playbook` is developer-guided and does not auto-merge or write migration changes without explicit file-level approval.

Codex skills for repeatable workflows are in `.agents/skills/`. Older Cursor-specific rules and skills under `.cursor/` are retained as migration history; use this file and `.agents/skills/` as the current guidance.
