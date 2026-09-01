# AI-Assisted Microservice Migration — Operating Model

Canonical operating model for the EuroSA Bank POC, aligned with the 1 September stakeholder meeting.

**Core message:** AI is not free-form architecture generation. AI reasons over evidence within architecture knowledge and patterns; humans remain accountable for decisions.

**Stakeholder terminology (1 Sep meeting):** Avoid a binary “deterministic vs non-deterministic” label for AI stages. Use three terms: **deterministic analysis** (no LLM), **pattern-constrained AI** (LLM within architecture knowledge), and **human decision** (gates). “Non-deterministic” here means LLM output can vary on repeat runs — not that architecture is unconstrained.

---

## Two dimensions

### Dimension 1 — Eight-stage pipeline (within one migration iteration)

```text
1 Discover  →  2 Ingest  →  3 Graph  →  4 Diagnose
       →  5 Hypothesize  →  6 Recommend  →  7 Plan  →  8 Guide
```

### Dimension 2 — Migration lifecycle (across the estate)

```text
        ┌─────────────────────────────┐
        │       Migration Phase N     │
        │  Discover → … → Guide       │
        │             ↓               │
        │          Validate           │
        └─────────────┬───────────────┘
                      │
                 Human feedback
                      │
                      ▼
        ┌─────────────────────────────┐
        │       Migration Phase N+1 │
        │  Discover → … → Guide       │
        └─────────────────────────────┘
```

Feedback can move **backward within a phase** — e.g. rejected hypothesis → refine evidence → re-hypothesize.

---

## Architecture knowledge layer

```text
                    ARCHITECTURE KNOWLEDGE
              Rules · Patterns · Principles · Skills
                             │
                             ▼
Source ──► Deterministic Evidence ──► AI Reasoning
          & Analysis                    │
              │                         ▼
              │                  Candidate Hypotheses
              │                         │
              └─────────────────────────┤
                                        ▼
                                Human Architecture
                                    Decision
                                        │
                                        ▼
                                  Migration Plan
                                        │
                                        ▼
                                  Engineering
                                        │
                                        ▼
                                  Validation
                                        │
                                        └────► Feedback
```

| Layer | Where it lives in POC | Role |
|-------|----------------------|------|
| Architecture knowledge | `.cursor/rules/`, `AGENTS.md`, skills, `landscape-manifest.yaml` | Constrains what AI may propose; encodes DDD/bounded-context patterns |
| Deterministic evidence & analysis | Stages 1–4, `diagnose.py`, graph builder | Repeatable facts and smells — no LLM |
| AI reasoning | Stages 5–7, `hypothesize.py`, `recommend.py` | Evidence-backed hypotheses and ADRs with confidence |
| Human decision | Approval gates (recommend, plan), Streamlit dashboard | Architects approve, modify, or block |
| Engineering | Stage 8 playbook, task assistant | Guided execution with diff review |
| Validation | Re-run diagnose, stakeholder report | Prove improvement before next phase |

---

## Deterministic vs AI-assisted vs human

| Stage | Mode | Repeatable? | LLM? | Human gate? |
|-------|------|-------------|------|-------------|
| 1 Discover | Deterministic | Yes | No | No |
| 2 Ingest | Deterministic (adapters) | Yes | No | Yes (ingest) |
| 3 Graph | Deterministic | Yes | No | No |
| 4 Diagnose | Deterministic | Yes | No | Yes (diagnose) |
| 5 Hypothesize | AI-assisted (mock if no key) | Same evidence → same mock | Yes | Yes (hypothesize) |
| 6 Recommend | AI-assisted | Evidence-grounded ADRs | Yes | **Required** |
| 7 Plan | Framework + AI context | Phases from ADRs + landscape | Partial | **Required** |
| 8 Guide | Framework + engineer | Playbook tasks, assisted diffs | Optional | Engineer review |

**Stages 1–4:** Same inputs produce the same outputs (auditable, compliance-friendly).

**Stages 5–7:** Outputs cite evidence and diagnosis; confidence scores flag uncertainty. Low confidence → more SME validation, not auto-approval.

**Stage 8:** Framework never auto-merges production code. Assisted tasks write only after per-file diff approval.

---

## Customer-facing story (deck without live demo)

```text
Current Estate
      │
      ▼
Discover → Evidence → Architecture Graph → Diagnosis
      │
      ▼
AI Context Hypotheses (confidence-scored)
      │
      ▼
Architecture Board
      │
      ├── Reject ───────► Refine evidence / Re-hypothesize
      │
      ▼
Approved Architecture (ADRs)
      │
      ▼
Migration Plan
      │
      ├── Reject / Modify ► Re-plan
      │
      ▼
Engineering Execution (playbook + diff review)
      │
      ▼
Validation (re-diagnose, report)
      │
      ├── Not improved ──► Re-diagnose / Re-plan
      │
      ▼
Next Migration Phase
```

---

## Re-entry and rejection paths

| Event | POC action today | Artifact / command |
|-------|------------------|-------------------|
| Reject recommend gate | Do not approve; edit ADRs or re-run recommend | `artifacts/recommend/adrs.yaml` |
| Modify hypothesis | Re-run hypothesize after ingest/graph refresh | `run --stage hypothesize` |
| Reject plan gate | Do not approve; adjust plan JSON or re-run plan | `artifacts/plan/migration-plan.json` |
| Low AI confidence | Review in dashboard; add evidence (traces, SME notes) | Hypothesis confidence in UI |
| Incomplete evidence | Flag in report; extend adapters or metadata | `metadata/`, ingest adapters |
| Post-phase validation failed | Re-run diagnose; compare reports | `cli report`, diagnose stage |
| SME overrides AI | Gate notes + manual ADR edit | `approve --notes "..."` |

Explicit **reject** CLI flag is not implemented — rejection is **withhold approval** and rework upstream stages.

---

## Low-confidence AI handling

1. **Evidence confidence** — each `EvidenceItem` has `confidence` (default 1.0); synthetic/trace data may be lower.
2. **Hypothesis confidence** — hypotheses ranked in recommend; low scores surface in report and Streamlit.
3. **Mock mode** — without `OPENAI_API_KEY`, deterministic mock hypotheses preserve demo repeatability.
4. **Human rule** — confidence &lt; threshold (e.g. 0.7) → architecture review required before gate approval (process, not automated block).

---

## Friday deliverable checklist

| Deliverable | Doc / artifact |
|-------------|----------------|
| A. Solution architecture | `docs/stakeholder-presentation.md`, `docs/target-architecture.md` |
| B. Eight-stage methodology | `docs/framework-methodology.md`, presentation stages |
| C. Iterative operating model | This document |
| D. Complexity & exceptions | `docs/migration-complexity-matrix.md` |
| E. Evidence of execution | EuroSA project `proj-*`, playbook, `target-contexts/`, demo script |

---

## POC boundary (do not merge)

| POC | Focus | This repo |
|-----|-------|-----------|
| **POC 1 — AI-assisted microservice migration** | Evidence → bounded contexts → guided migration | **This repository** |
| **POC 2 — ATM** | Separate workstream | Not in this repo |

References to "both cases" in meetings mean **two POCs**, not two scenarios inside the migration POC.

---

## Related

- [Framework methodology](framework-methodology.md)
- [Migration complexity matrix](migration-complexity-matrix.md)
- [POC demo script](poc-demo-script.md)
- [Stakeholder presentation](stakeholder-presentation.md)
