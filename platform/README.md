# Migrate Framework

AI-driven microservice-to-DDD migration pipeline with 8 stages: discover, ingest, graph, diagnose, hypothesize, recommend, plan, playbook.

## Quick start

```bash
cd platform
pip install -e ".[dev]"
migrate-framework init --name "EuroSA Bank" --source ../sample-bank --landscape ../sample-bank/landscape-manifest.yaml
```

Or run the full pipeline:

```powershell
.\scripts\run_pipeline.ps1
```
