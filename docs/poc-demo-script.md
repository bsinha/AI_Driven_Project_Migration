# POC Demo Script

## Prerequisites

```powershell
cd platform
pip install -e ".[dev]"
copy .env.example .env   # optional OPENAI_API_KEY
```

## Demo flow (15 minutes)

### 1. Initialize project (1 min)

```powershell
python -m migrate_framework.cli init --name "EuroSA Bank" --source ../sample-bank --landscape ../sample-bank/landscape-manifest.yaml
```

Note the `project-id`.

### 2. Run deterministic stages (3 min)

```powershell
python -m migrate_framework.cli run --project-id <id> --stage discover --through diagnose
```

Show: 16 services detected, java-spring-boot stack, health report with granularity smell.

### 3. AI hypotheses (2 min)

```powershell
python -m migrate_framework.cli run --project-id <id> --stage hypothesize
python -m migrate_framework.cli run --project-id <id> --stage recommend
```

Without API key: mock hypotheses from landscape `target_bounded_contexts`.

### 4. Human validation gate (2 min)

Open Streamlit: `streamlit run migrate_framework/ui/app.py`

Demonstrate **Approve** / **Modify** on recommendation. Contrast with "what auto-merge would do wrong" on false cohesion.

```powershell
python -m migrate_framework.cli approve --project-id <id> --gate recommend
```

### 5. Migration plan (2 min)

```powershell
python -m migrate_framework.cli run --project-id <id> --stage plan
python -m migrate_framework.cli approve --project-id <id> --gate plan
```

Walk Phase 1: Customer Management consolidation.

### 6. Developer playbook (2 min)

```powershell
python -m migrate_framework.cli run --project-id <id> --stage playbook
```

Emphasize: tasks for **developer execution**, not automatic code merge.

### 7. Quick full run

```powershell
..\scripts\run_pipeline.ps1 -AutoApprove
```

## Success criteria checklist

- [ ] 16-service topology visible
- [ ] Smells detected with evidence
- [ ] 4 bounded contexts recommended
- [ ] Approval gates demonstrated
- [ ] Playbook shows manual migration tasks
