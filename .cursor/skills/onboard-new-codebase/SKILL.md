---
name: onboard-new-codebase
description: Registers a new microservice codebase with the migration framework. Use for stage 1 discover on Java, .NET, or polyglot estates.
---

# Onboard New Codebase

```bash
cd platform
python -m migrate_framework.cli init \
  --name "MyBank" \
  --source /path/to/codebase \
  --landscape /path/to/landscape.yaml   # optional
python -m migrate_framework.cli run --project-id <id> --stage discover
```

Stack detection selects adapters automatically (Java Maven, .NET stubs, shared OpenAPI/SQL).
