# Agent Orchestration

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
