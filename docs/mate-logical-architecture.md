# MATE — Logical Architecture (v2)

**Modernization & Architecture Transformation Engine**

Canonical logical architecture for MATE. Use this document for stakeholder decks, architecture reviews, and drawing-tool exports (Mermaid, draw.io, Lucidchart).

**Related:** [Operating model](operating-model.md) · [Framework methodology](framework-methodology.md) · [Target architecture](target-architecture.md) · [V&V roadmap](friday-roadmap-governance-vv.md)

---

## Legend

| Style | Meaning |
|-------|---------|
| **Solid components** | Implemented in the EuroSA Bank POC (`platform/migrate_framework/`) |
| *Dashed / italic components* | Roadmap — designed in, not fully built |
| **Gate** | Human approval required before advancing |
| **V&V** | Verification (built correctly) + Validation (business capability parity) |

**Stage 8 naming:** The pipeline stage is `playbook` in code and CLI. **Guide** is the stakeholder-facing label for the same stage — assisted execution, not autonomous transformation.

> **Core rule:** MATE never auto-merges production services. Stage 8 produces playbook tasks and diff-reviewed scaffolds; engineers execute and validate.

---

## 1. Platform overview

```mermaid
flowchart TB
    subgraph personas [Users and personas]
        BS[Business stakeholder<br/>Vision and outcomes]
        EA[Enterprise architect<br/>Architecture decisions]
        AO[Application owner<br/>Assessment and planning]
        ENG[Engineer / migration team<br/>Guided transformation]
        GOV[Governance / risk<br/>Compliance and traceability]
    end

    subgraph access [Access layer — POC]
        CLI[CLI<br/>Pipeline run · scope · phase close]
        UI[Web UI — Streamlit<br/>Dashboard · governance · playbook]
        API[API — FastAPI<br/>CI/CD · automation]
    end

    subgraph sources [Source systems — any technology]
        REPO[Code repositories<br/>GitHub · GitLab · Azure DevOps]
        ART[Application artifacts<br/>Source · configs · builds]
        ARCH[Architecture assets<br/>Diagrams · ADRs · specs]
        RUN[Runtime and ops data<br/>APIs · DBs · traces · logs]
        CLOUD[Cloud · containers · IaC · CMDB]
    end

    subgraph mate [MATE core platform]
        subgraph pipeline [Transformation pipeline — 8 stages]
            direction LR
            subgraph det [Part A — deterministic analysis]
                S1[1 Discover]
                S2[2 Ingest]
                S3[3 Graph]
                S4[4 Diagnose]
            end
            subgraph ai [Part B — AI-assisted reasoning]
                S5[5 Hypothesize]
                S6[6 Recommend]
                S7[7 Plan]
                S8[8 Guide / Playbook<br/>Human-reviewed scaffolds only]
            end
            S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8
        end
        ORCH[Pipeline orchestrator<br/>State · gates · iteration · reporting]
        pipeline --> ORCH
    end

    subgraph intel [Architecture intelligence layer]
        direction TB
        EVD[Evidence store<br/>Normalized EvidenceItem]
        GRF[Graph store<br/>NetworkX POC · Neo4j roadmap]
        KB[Knowledge base<br/>Rules · patterns · skills · smell catalog]
        CTX[Prompt and context assembly<br/>Evidence + rules → LLM input]
        LLM[LLM integration<br/>OpenAI · Azure · Anthropic]
        EVD --> GRF
        EVD --> CTX
        KB --> CTX
        GRF --> CTX
        CTX --> LLM
    end

    subgraph governance [Governance and human oversight]
        DEC[Decision governance<br/>Gates · ADRs · scope · waivers]
        ASS[Assurance governance<br/>V&V · capability matrix · phase close]
        COLLAB[Collaboration<br/>Reject · request evidence · comments roadmap]
    end

    subgraph storage [Data and storage layer — POC]
        PS[Project store<br/>project.json · state]
        AS[Artifact store<br/>Per-stage YAML/JSON]
        AUD[Audit and decision log<br/>Gate records · timestamps]
    end

    subgraph vv [Verification and validation — POC]
        CM[Capability traceability matrix]
        CT[Contract test tasks]
        RD[Re-diagnose and phase snapshots]
        SME[SME sign-off]
    end

    subgraph outcomes [Target outcomes — technology agnostic]
        O1[Monolith to modular]
        O2[Microservices to domain-aligned services]
        O3[Cloud modernization]
        O4[Technology upgrades]
        O5[Other transformation scenarios]
    end

    personas --> access
    access --> mate
    sources --> S1
    sources --> S2
    mate --> intel
    mate --> governance
    mate --> storage
    intel --> pipeline
    S6 -.->|Gate| DEC
    S7 -.->|Gate| DEC
    S8 --> vv
    vv --> ASS
    vv -->|Feedback| S4
    vv -->|Next wave| S1
    mate --> outcomes
```

---

## 2. Pipeline and gates (detail)

```mermaid
flowchart LR
    subgraph deterministic [Stages 1–4 — no LLM]
        D1[Discover<br/>Inventory · stack profile]
        D2[Ingest<br/>Adapter evidence]
        D3[Graph<br/>Knowledge graph]
        D4[Diagnose<br/>Smells · metrics]
    end

    subgraph assisted [Stages 5–7 — evidence-backed AI]
        A5[Hypothesize<br/>Candidate contexts]
        A6[Recommend<br/>ADRs · capability matrix]
        A7[Plan<br/>Phased roadmap]
    end

    G6{{Recommend gate<br/>Approve · reject · modify}}
    G7{{Plan gate<br/>Approve before playbook}}

    P8[Stage 8 Guide / Playbook<br/>Task checklist · assisted diffs<br/>No auto-merge]

    D1 --> D2 --> D3 --> D4 --> A5 --> A6 --> G6 --> A7 --> G7 --> P8

    G6 -->|Reject| A5
    G6 -->|Request evidence| D2
    G7 -->|Reject| A6
```

| Stage | POC module | Repeatable? | LLM? | Human gate? |
|-------|------------|-------------|------|-------------|
| 1 Discover | `ingestion/discover.py` | Yes | No | No |
| 2 Ingest | `ingestion/adapters/*` | Yes | No | Optional |
| 3 Graph | `graph/builder.py` | Yes | No | No |
| 4 Diagnose | `analysis/diagnose.py` | Yes | No | Optional |
| 5 Hypothesize | `analysis/hypothesize.py` | Mock deterministic | Yes | Optional |
| 6 Recommend | `analysis/recommend.py` | Evidence-grounded | Yes | **Required** |
| 7 Plan | `migration/planner.py` | From ADRs + landscape | Partial | **Required** |
| 8 Guide / Playbook | `migration/playbook.py` | Engineer-executed | Optional assist | Diff review |

---

## 3. Verification and validation loop

Answers: *Does TO-BE still serve the same business capabilities as AS-IS?*

```mermaid
flowchart TB
    subgraph baseline [Before migration — AS-IS baseline]
        B1[Ingest OpenAPI · services · traces]
        B2[Capability rows from evidence]
        B3[Diagnose baseline snapshot]
    end

    subgraph design [Design-time validation — Stage 6–7]
        D1[Capability matrix<br/>mapped · gap · deferred]
        D2[ADR approval gate]
        D3[Plan phase scope]
    end

    subgraph execute [Execution verification — Stage 8]
        E1[Contract tests vs legacy OpenAPI]
        E2[ACL / strangler routing]
        E3[Parallel run · shadow traffic]
        E4[Schema migration reconciliation]
    end

    subgraph close [Post-phase validation]
        C1[Golden-path E2E journeys]
        C2[Re-diagnose — smells vs baseline]
        C3[V&V coverage 100% · zero gap rows]
        C4[SME sign-off · phase close]
    end

    B1 --> B2 --> D1
    B3 --> C2
    D1 --> D2 --> D3 --> E1
    E1 --> E2 --> E3 --> E4 --> C1
    C1 --> C2 --> C3 --> C4
    C4 -->|Phase N+1| B1
    C3 -->|Gap found| D3
```

**POC artifacts:** `vv/capability_matrix.py` · Governance → V&V panel · Playbook contract-test scaffolds · `pipeline/phase_snapshot.py` readiness score.

---

## 4. Architecture intelligence flow

Shows how evidence becomes constrained AI output (today: JSON context assembly; roadmap: RAG + vector store).

```mermaid
flowchart LR
    SRC[Source repo and metadata] --> ADP[Ingestion adapters]
    ADP --> EVD[(Evidence store)]
    EVD --> GRPH[(Graph — NetworkX)]
    EVD --> DIAG[Diagnose engine]
    RULES[(Knowledge base<br/>rules · skills · smells)]
    EVD --> ASM[Context assembly]
    GRPH --> ASM
    DIAG --> ASM
    RULES --> ASM
    ASM --> LLM[LLM providers]
    LLM --> HYP[Hypotheses]
    HYP --> ADR[ADRs + capability matrix]
    ADR --> PLAN[Migration plan]
```

*Roadmap:* Vector store and embeddings between Evidence store and Context assembly for semantic retrieval (RAG).

---

## 5. POC vs roadmap matrix

| Component | POC (today) | Roadmap |
|-----------|-------------|---------|
| **Graph store** | NetworkX in-memory | Neo4j / persistent graph DB |
| **Vector store** | — | Embeddings for RAG |
| **Knowledge base** | `.cursor/rules/`, skills, smell catalog, manifest | Centralized pattern library UI |
| **Runtime ingestion** | Synthetic traces (`metadata/`), `TraceAdapter` | Live APM, logs, CMDB |
| **Cloud / IaC adapters** | — | Terraform, K8s, ARM/Bicep |
| **Collaboration** | Reject, request-evidence, decision log | Threaded comments, evidence requests |
| **Audit store** | `decision_log` in project metadata | Immutable enterprise audit service |
| **Multi-LLM synthesis** | Per-provider runs in `llm_providers.py` | Orchestrated consensus / voting |
| **Contract tests** | Playbook scaffolds | CI-wired OpenAPI diff runners |
| **.NET adapters** | Registered stubs | Full parity with Java |

---

## 6. Component-to-code mapping

| Diagram box | Repository path |
|-------------|-----------------|
| CLI | `platform/migrate_framework/cli.py` |
| Web UI | `platform/migrate_framework/ui/app.py` |
| API | `platform/migrate_framework/api/main.py` |
| Pipeline orchestrator | `platform/migrate_framework/pipeline/orchestrator.py` |
| Ingestion adapters | `platform/migrate_framework/ingestion/adapters/` |
| Graph builder | `platform/migrate_framework/graph/builder.py` |
| Diagnose | `platform/migrate_framework/analysis/diagnose.py` |
| Hypothesize / LLM | `platform/migrate_framework/analysis/hypothesize.py`, `llm_providers.py` |
| Recommend | `platform/migrate_framework/analysis/recommend.py` |
| Plan | `platform/migrate_framework/migration/planner.py` |
| Guide / Playbook | `platform/migrate_framework/migration/playbook.py`, `task_assistant.py` |
| Decision governance | `platform/migrate_framework/pipeline/governance.py`, `scope.py` |
| Capability matrix (V&V) | `platform/migrate_framework/vv/capability_matrix.py` |
| Phase snapshots | `platform/migrate_framework/pipeline/phase_snapshot.py` |
| Project / artifact store | `platform/migrate_framework/pipeline/project_store.py` |

---

## 7. Box labels for drawing tools

Copy into ChatGPT, draw.io, Lucidchart, or PowerPoint. Group boxes left-to-right as in section 1.

### Row 1 — Personas
- Business Stakeholder — Vision & Outcomes
- Enterprise Architect — Architecture Decisions
- Application Owner — Assessment & Planning
- Engineer / Migration Team — Guided Transformation
- Governance / Risk — Compliance & Traceability

### Row 2 — Access layer `[POC]`
- **CLI** — Pipeline execution, batch scope, phase close, CI scripts
- **Web UI (Streamlit)** — Dashboard, governance, AS-IS→TO-BE, playbook, assessment report
- **API (FastAPI)** — Projects, run stage, approve/reject, status

### Row 3 — Source systems `[mixed]`
- Code Repositories — GitHub, GitLab, Azure DevOps, Bitbucket `[POC: local path]`
- Application Artifacts — Source, binaries, configs, builds `[POC]`
- Architecture Assets — Diagrams, ADRs, specifications `[POC: manifest + metadata]`
- Runtime & Ops Data — APIs, databases, traces, logs `[POC: synthetic; roadmap: live]`
- Cloud / IaC / CMDB `[roadmap]`

### Row 4 — MATE core — Pipeline `[POC]`

**Part A — Deterministic analysis (establish architectural facts)**
1. Discover — Analyze and identify artifacts
2. Ingest — Extract and normalize evidence
3. Graph — Build architecture knowledge graph
4. Diagnose — Detect smells and health metrics

**Part B — AI-assisted reasoning (generate options and guidance)**
5. Hypothesize — Candidate transformation options
6. Recommend — Prioritize target architecture + **capability matrix**
7. Plan — Phased migration roadmap
8. Guide / Playbook — Execution tasks; **assisted scaffolds with diff review; no auto-merge**

**Orchestrator** — State, workflow, human gates, iteration/re-entry, reporting

### Row 5 — Architecture intelligence `[mixed]`
- Evidence Store — Normalized `EvidenceItem` + artifacts `[POC]`
- Graph Store — NetworkX `[POC]` → Neo4j `[roadmap]`
- Knowledge Base — Rules, patterns, principles, skills `[POC: repo files]`
- Prompt & Context Assembly — Evidence + rules → LLM input `[POC]`; RAG guardrails `[roadmap]`
- LLM Integration — OpenAI, Azure, Anthropic `[POC]`

### Row 6 — Governance `[mixed]`
- **Decision governance** — Approval workflows, ADRs, scope, phase management, waivers `[POC]`
- **Assurance governance** — V&V, capability matrix review, phase close, readiness score `[POC]`
- Policy & compliance — Standards, security, risk `[roadmap]`
- Collaboration — Comments, evidence requests `[partial POC]`

### Row 7 — V&V `[POC]`
- Capability traceability matrix (AS-IS API → TO-BE context)
- Contract tests (legacy OpenAPI pin)
- Re-diagnose and phase snapshots
- SME sign-off before phase close

### Row 8 — Data and storage `[POC]`
- Project Store — State, configuration, progress
- Artifact Store — Reports, plans, playbooks per stage
- Graph Database — In-memory graph (Neo4j roadmap)
- Vector Store — `[roadmap]`
- Audit & Log Store — Gate decisions, timestamps (immutable store roadmap)

### Row 9 — Target outcomes
- Monolith → Modular
- Monolith + Frontend → Services
- Microservices → Domain-aligned services
- Cloud Modernization
- Technology Upgrades
- Other transformation scenarios

### Connectors (important arrows)
- Source systems → Discover + Ingest
- Stages 6 & 7 → **Gate** → Decision governance
- Stage 8 → V&V → Assurance governance
- V&V failure → re-Plan or re-Diagnose (feedback loop)
- Phase close → next wave → Discover (incremental transformation)

---

## 8. Changes from diagram v1 (ChatGPT)

| v1 issue | v2 resolution |
|----------|----------------|
| Neo4j shown as current | Labeled NetworkX POC; Neo4j roadmap |
| No V&V layer | Dedicated V&V subgraph + section 3 loop |
| Stage 8 implied automation | Explicit “no auto-merge” on Stage 8 box |
| CLI missing from access | CLI alongside Streamlit and FastAPI |
| Intelligence layer as four silos | Section 4 shows evidence → graph → context → LLM chain |
| Governance monolithic | Split decision vs assurance governance |
| No POC honesty | Legend + section 5 matrix throughout |

---

## 9. Export notes

- **Mermaid:** Sections 1–4 render in GitHub, VS Code, and most markdown viewers.
- **Stakeholder deck:** Export section 1 as PNG; add legend slide from section “Legend”.
- **ARB pack:** Include sections 3 (V&V), 5 (POC vs roadmap), and 6 (code mapping).
