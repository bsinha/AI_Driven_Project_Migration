# Friday Roadmap — Governance, UI Analytics, V&V, Multi-LLM

Design proposals for internal readiness (5 Sep) and Chris presentation.  
**POC 1 only** — AI-assisted microservice migration (this repository).

---

## 1. Where you are heading (confirmed)

You are moving from **“pipeline that produces artifacts”** to **“governed modernization operating system”**:

- Explicit **reject / modify / approve** with captured reasoning
- **Cannot advance** past mandatory decisions without resolution (or documented waiver)
- **Per-proposal assistance** — AS-IS vs TO-BE, mandatory vs optional, benefit of acceptance
- **Stage analytics in the UI** — not only downloadable reports
- **V&V** — prove TO-BE covers AS-IS business functionality
- **Multi-LLM** — provider choice and holistic recommendation

---

## 2. Rejection & modification — proposed model

### 2.1 Today (gaps)

| Capability | Today |
|------------|-------|
| Approve gate | `approve()` sets `approved=True`, optional `notes` |
| Reject | **No** — only withhold approval |
| Rejection reason | `notes` on approve only; no structured reason |
| Modify | Manual edit of YAML/JSON artifacts; no workflow |
| Block pipeline | **Yes** — `can_run()` blocks if previous **required** gate not approved |
| Re-run stage after reject | Possible via CLI/UI run; no formal “rework” state |
| Decision audit | `approved_by`, `approved_at` only |

**Rule today:** For **required** gates (ingest, diagnose, hypothesize, recommend, plan), you **cannot** run the next stage until the previous required gate is **approved**. Withholding approval **blocks** progress. There is no “proceed with rejected item skipped” for mandatory ADRs.

### 2.2 Proposed gate decision model

Extend `ApprovalGate` (and ADR-level decisions) with:

```text
status: pending | approved | rejected | modified | waived
decision_by, decision_at
reason_code: enum (e.g. insufficient_evidence, wrong_boundary, risk_too_high, sme_disagreement)
reason_text: free text (required on reject/modify)
parent_decision_id: link to superseded decision (iteration)
```

### 2.3 What happens when a proposal is rejected?

```text
Architect reviews Recommend gate (ADRs / target architecture)
        │
        ├── APPROVE ──► Plan stage unlocked
        │
        ├── MODIFY ──► reason_text + edited ADRs saved as new version
        │              └──► optional re-run Recommend OR manual artifact edit
        │              └──► gate stays pending until re-approval
        │
        └── REJECT ──► reason_code + reason_text stored (mandatory)
                       └──► gate remains NOT approved → Plan BLOCKED
                       └──► rework path chosen:
                             • Re-hypothesize (new candidates)
                             • Add evidence (re-ingest / metadata)
                             • SME workshop (manual evidence items)
                       └──► after rework → re-run upstream stage → new review
```

**Collect reasoning?** **Yes — required** on reject and modify. Optional on approve (acceptance rationale helps audit).

**Proceed without approval of rejected item?**

| Item type | Can skip? | Rule |
|-----------|-----------|------|
| **Required gate** (recommend, plan) | **No** | Pipeline blocked until approved, modified-and-approved, or **waived** with executive sign-off |
| **Optional gate** (discover, graph, playbook) | Yes | Never blocks |
| **Individual ADR** (within recommend) | Partial | Defer non-critical ADR to later phase if marked **optional**; **mandatory** ADRs must be approved or waived before plan |
| **Playbook task** | Yes | Tasks are execution backlog; skip/defer with owner consent |

**Waived** = documented exception (“accept risk, proceed anyway”) with approver + reason — for Friday **process + UI**, not full automation.

### 2.4 Presentation slide (Friday)

One flowchart: **Approve / Modify / Reject / Waive** with block vs rework arrows. Explicit: *“Rejected mandatory architecture decisions block the pipeline until resolved or formally waived.”*

---

## 3. Per-item assistance — AS-IS / TO-BE / mandatory / benefit

### 3.1 Proposal item card (UI pattern)

Each hypothesis, ADR, plan phase, and playbook task should show:

| Field | Purpose |
|-------|---------|
| **Title** | What is being proposed |
| **Type** | Hypothesis · ADR · Phase · Playbook task |
| **Mandatory?** | Blocks gate if not accepted (ADR-level) |
| **AS-IS snapshot** | Services, APIs, DBs, smells affected |
| **TO-BE preview** | Target context, consolidated services, unified API sketch |
| **Evidence links** | Clickable evidence IDs / smell refs |
| **Confidence** | AI or deterministic score |
| **Benefit if accepted** | e.g. removes shared DB, cuts sync chain depth |
| **Risk if rejected/deferred** | e.g. plan blocked, coupling remains |
| **Assistance actions** | Generate scaffold · View diff · View context map slice |

### 3.2 Mandatory vs optional (proposed taxonomy)

| Level | Mandatory examples | Optional examples |
|-------|-------------------|-------------------|
| **Gate** | recommend, plan | discover, graph, playbook |
| **ADR** | Context consolidation for Phase 1 scope | Async payment ADR if phase 2 |
| **Plan phase** | Phase 1 if in program scope | Decommission phase timing |
| **Playbook task** | Contract tests before cutover | Extra documentation |

Mark in artifact JSON: `"mandatory": true|false`, `"blocks_gate": true|false`.

### 3.3 TO-BE architecture visibility (Friday minimum)

**Presentation + UI (no new graph engine required):**

1. **Context map** — static Mermaid in deck + `target-architecture.md`
2. **Per-phase TO-BE panel** — table: AS-IS services → TO-BE context (from plan + ADRs)
3. **Assisted scaffold** — `target-contexts/<context>/` tree preview in Streamlit
4. **Before/after metrics** — service count, smell count, sync chain length (diagnose compare)

**Post-Friday:** interactive context-map from graph JSON.

---

## 4. Stage analytics in UI (vs download-only report)

### 4.1 Today

- Per-stage artifact viewers in `artifact_views.py` ✓
- Pipeline stage selector ✓
- Download MD/HTML report ✓
- **Missing:** unified **analytics dashboard** per stage, before/after compare, decision log

### 4.2 Friday UI additions (prioritized)

| Priority | Feature | Stage |
|----------|---------|-------|
| **P0** | **Stage summary metrics** at top of each stage panel (reuse report sections) | All |
| **P0** | **Decision log** panel — gate decisions + reasons | Governance |
| **P0** | **AS-IS vs TO-BE summary** tab from ADRs + plan | Recommend, Plan |
| **P1** | **Diagnose compare** — two diagnose runs side-by-side | Diagnose |
| **P1** | **Evidence coverage** — % smells with linked evidence | Ingest, Diagnose |
| **P2** | Embedded HTML report tab (not only download) | All |

Reuse `pipeline_report.py` generators inside Streamlit — **one source of truth** for download and on-screen.

---

## 5. Verification & Validation (V&V)

### 5.1 Definitions

| | Verification | Validation |
|---|--------------|------------|
| **Question** | Did we build the TO-BE correctly? | Does TO-BE meet business needs (AS-IS parity)? |
| **When** | During / after engineering (Stage 8) | After phase cutover + on gate review |
| **POC artifacts** | Contract tests, diffs applied, compile/test | Capability traceability matrix |

### 5.2 Capability traceability matrix (core V&V artifact)

```text
Business capability (or API operation)
    ← AS-IS: service(s) + endpoint(s) + evidence ref
    → TO-BE: bounded context + endpoint/event + playbook task status
    Status: mapped | partial | gap | deferred
    Validation: contract test id | manual SME sign-off
```

**Sources:**

- AS-IS: OpenAPI adapters, landscape manifest, synthetic traces
- TO-BE: unified OpenAPI drafts, ADRs, `target-contexts/` scaffolds

### 5.3 V&V stages in pipeline

```text
Stage 4 Diagnose     → baseline AS-IS health (verification baseline)
Stage 6 Recommend    → validate proposed boundaries against capability map
Stage 8 Playbook       → contract tests + parallel-run tasks
Post-phase             → re-diagnose (verification: smells reduced)
Post-phase             → capability matrix review (validation: no gap rows)
```

### 5.4 Friday deliverable

- **Presentation:** V&V slide with traceability matrix example (Customer Management — 5 APIs → 1 context API)
- **POC:** `artifacts/vv/capability-matrix.json` generated from OpenAPI evidence (script or planner extension) — **stretch**; matrix in deck is **must**

### 5.5 “Foolproof” statement (honest)

> We verify structural improvement (metrics, tests, contracts) and validate business coverage via explicit capability mapping and human SME sign-off — not fully automated proof of domain correctness.

---

## 6. Multi-LLM support

### 6.1 Today

- `OPENAI_API_KEY` + `OPENAI_MODEL` (default `gpt-4o-mini`) in `hypothesize.py`
- Mock fallback when no key
- Single provider, single model, single response

### 6.2 Proposed architecture

```text
LLMProvider (interface)
  ├── OpenAIProvider
  ├── AzureOpenAIProvider
  └── AnthropicProvider (optional)

MultiLLMOrchestrator
  ├── run_all(providers, prompt) → list[ModelResult]
  ├── store: artifacts/hypothesize/hypotheses-openai.json, hypotheses-azure.json
  └── synthesize(results) → holistic recommendation + dissent notes
```

**Config:** `.env` — `LLM_PROVIDERS=openai,azure`, per-provider keys/models.

**Holistic recommendation:**

- Agreement → higher confidence
- Divergence → surface in UI as “models disagree” + human required
- Never auto-merge conflicting boundaries

### 6.3 Friday scope

| Deliverable | POC code | Presentation |
|-------------|----------|--------------|
| Provider interface + 2 providers | Stretch | **Architecture diagram** |
| Side-by-side model outputs in UI | Stretch | **Slide: multi-model consensus** |
| Env-based provider switch | **P1** — single alternate provider | Mention in deck |

---

## 7. Additional items you may have missed

1. **Decision audit trail** — immutable log of all gate/ADR decisions (compliance)
2. **Iteration counter** — “hypothesis round 2” visible in UI
3. **Escalation** — stuck after N rejections → flag for architecture board
4. **Evidence gap workflow** — “request SME evidence” task type in playbook
5. **Role-based views** — architect (gates, ADRs) vs engineer (playbook) vs PM (plan timeline)
6. **ADR versioning** — `adrs-v1.yaml`, `adrs-v2.yaml` after modify
7. **Waiver registry** — formal exception record for mandatory items
8. **Confidence threshold policy** — e.g. &lt;0.7 cannot approve without waiver
9. **Notification / export** — email or ADO comment with decision summary (post-Friday)
10. **Separation from ATM POC** — no shared gate model in slides

---

## 8. Friday cut — POC vs presentation

### Must have (presentation)

- [ ] Reject / modify / approve / waive flowchart
- [ ] Mandatory vs optional table
- [ ] Per-item benefit + TO-BE preview (Customer Management example)
- [ ] Stage analytics story (UI screenshots or mock)
- [ ] V&V + capability traceability example
- [ ] Multi-LLM positioning (diagram; live optional)
- [ ] Three-way terminology (deterministic / pattern-constrained AI / human)

### Must have (POC — minimal code)

- [ ] Reject + reason in UI (`notes` required on reject; set `approved=False`, store `status=rejected`)
- [ ] Decision log in Streamlit (from gate fields + notes)
- [ ] Stage summary metrics on stage panel (call report helpers)
- [ ] `mandatory` flag on ADRs in recommend output (display in UI)

### Stretch (if time)

- [ ] `capability-matrix.json` generator
- [ ] Diagnose before/after compare
- [ ] Second LLM provider
- [ ] Embedded HTML report tab

### Explicitly defer

- Production-grade multi-tenant UI
- Full autonomous coding
- Jira/ADO sync
- Interactive live context-map editor

---

## 9. Related docs

- [Operating model](operating-model.md)
- [Meeting minutes 1 Sep](meeting-minutes-2026-09-01.md)
- [Complexity matrix](migration-complexity-matrix.md)
