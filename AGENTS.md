# Agent Orchestration

## Project standards

- The migration framework core stays technology-agnostic; stack-specific logic belongs in ingestion adapters.
- Stages discover, ingest, graph, and diagnose are deterministic. AI stages must use evidence-backed inputs and outputs; recommendation and plan require human approval.
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

- Use `explore` subagent to map granular-services before editing
- Use `over-split-microservice` skill only for POC setup
- **Never** refactor toward clean architecture — smells are intentional

## Analysis work (`platform/`)

- Use `bounded-context-analysis` skill before OpenAI calls
- Use `explore` (medium) for ingestion → graph → analysis flow
- Use `bugbot` only when user explicitly requests code review

## Parallel patterns

- Launch parallel `explore` agents for Java scanner, OpenAPI parser, metadata loader
- One agent drafts ADRs while another updates architecture docs

## Pipeline order

discover → ingest → graph → diagnose → hypothesize → recommend → [gate] → plan → [gate] → playbook

Codex skills for repeatable workflows are in `.agents/skills/`. Older Cursor-specific rules and skills under `.cursor/` are retained as migration history; use this file and `.agents/skills/` as the current guidance.
