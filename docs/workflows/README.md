# Workflows

## W0: Onboard new codebase

1. `migrate-framework init --name X --source /path/to/repo`
2. Run discover → ingest
3. Adapters auto-detect stack (Java, .NET stub, shared)

## W2: Full pipeline

See `docs/poc-demo-script.md` and skill `run-pipeline-stage`.

## Cursor hooks (optional)

If permitted in your environment, add `.cursor/hooks.json` with sessionStart hook per plan. Fallback: use `AGENTS.md` and skills.
