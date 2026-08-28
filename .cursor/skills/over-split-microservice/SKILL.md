---
name: over-split-microservice
description: Splits a well-bounded service into granular modules with intentional smells for POC setup. Use only on sample-bank landscape setup.
---

# Over-Split Microservice (POC only)

1. Edit `sample-bank/landscape-manifest.yaml` with new service entry
2. Run: `python scripts/generate_granular_services.py`
3. Inject smells: shared DB in `application.yml`, sync deps in `eurosa.downstream`
4. Update `metadata/change-coupling/` and traces if topology changes
5. Re-run pipeline ingest stage

Do not use on production codebases.
