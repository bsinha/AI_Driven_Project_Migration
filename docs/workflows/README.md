# Workflows

## W0: Onboard new codebase

1. `migrate-framework init --name X --source /path/to/repo`
2. Run discover → ingest
3. Adapters auto-detect stack (Java, .NET stub, shared)

## W2: Full pipeline

See `docs/poc-demo-script.md` and skill `run-pipeline-stage`.

## Codex guidance

Repository-wide instructions live in `AGENTS.md`; reusable task workflows live in `.agents/skills/`. Follow those instructions when working through the pipeline. No editor hooks are required.
