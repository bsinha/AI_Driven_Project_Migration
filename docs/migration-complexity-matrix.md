# Migration Complexity & Exception Matrix

Maps real-world migration complexities to framework detection, AI role, human decision, and **current POC coverage**.

Use this for stakeholder conversations: *"What happens when the straightforward path doesn't work?"*

Legend: **Implemented** · **Partial** · **Process only** · **Gap**

---

## Matrix

| Scenario | What can go wrong? | How framework detects it | AI role | Human decision | POC coverage |
|----------|-------------------|--------------------------|---------|----------------|--------------|
| **Shared database** | Multiple contexts own same data | DB/table graph, `shared_database` smell | Propose ownership / consolidation options | Decide data ownership | **Implemented** — EuroSA `customer_db` |
| **Distributed business rule** | Rule spread across services | Code/deps via adapters; manifest smells | Identify likely capability grouping | Validate domain boundary | **Partial** — deps + manifest; no deep code rule mining |
| **Long synchronous chain** | Runtime coupling, latency | Dependency graph, `sync_rest_chain` smell | Suggest decoupling (events/saga ADR) | Approve API/event strategy | **Implemented** — payment chain in sample |
| **Cross-context transaction** | Strong consistency requirement | Transaction evidence (limited) | Propose saga / eventual consistency | Decide consistency model | **Gap** — no distributed txn tracing yet |
| **Shared library** | Hidden coupling | Maven/csproj dependency adapters | Assess consolidation impact | Decide ownership | **Partial** — build deps, not runtime lib usage |
| **Shared event/topic** | Multiple consumers, unclear ownership | Trace/metadata adapters | Suggest event ownership | Validate contract | **Partial** — synthetic traces in `metadata/` |
| **Circular dependency** | Contexts depend on each other | Graph cycle detection | Suggest restructuring | Architecture decision | **Partial** — paths in graph; no dedicated cycle smell |
| **Service with multiple capabilities** | Poor cohesion | Granular decomposition smell, cohesion metrics | Suggest decomposition or merge | Decide boundary | **Implemented** — fragmentation score |
| **Data migration** | DB cannot split immediately | Schema/access from SQL adapters | Propose migration sequence in plan | Approve migration strategy | **Partial** — playbook + assisted SQL drafts |
| **Legacy / undocumented behaviour** | Evidence incomplete | Evidence count, source tags | Flag uncertainty in narrative | SME validation | **Process** — manual metadata supplement |
| **AI low-confidence result** | Insufficient evidence | Hypothesis/ADR confidence scores | Ask for more evidence (narrative) | Decide whether to proceed | **Implemented** — scores in UI/report |
| **Rejected architecture recommendation** | Wrong bounded context | N/A (human) | Re-run with refined prompt/evidence | Reject gate, rework | **Process** — withhold approve, re-run stages |
| **Validation shows no improvement** | Migration did not reduce smells | Re-run diagnose, compare metrics | Re-plan narrative | Re-diagnose / re-plan | **Implemented** — demo script step |

---

## EuroSA POC — demonstrated scenarios

| Scenario | Where to see it |
|----------|-----------------|
| Shared database | 5 customer services → `customer_db`; diagnose smell catalog |
| Sync chain | Payment initiation → validation → execution → status |
| Granular decomposition | 16 services vs 4 target contexts |
| Low-confidence / mock AI | Run without `OPENAI_API_KEY` |
| Human gates | Recommend + plan approval in Streamlit |
| Assisted execution | Phase 1 playbook → `target-contexts/customer-management/` |
| Re-diagnose | `run --stage diagnose` after phase work |

---

## Wednesday validation workshop (suggested)

For each **Partial** or **Gap** row, prepare a 2-minute narrative:

1. **What we detect today** (artifact or dashboard screen)
2. **What AI proposes** (hypothesis or ADR excerpt)
3. **What human must decide**
4. **Honest gap** and near-term mitigation (metadata, adapter, or process)

Do **not** claim full automation for Gap rows — document the **routing to human decision**.

---

## Detection reference (code)

| Smell / signal | Source |
|----------------|--------|
| `shared_database` | `diagnose.py` — `_database_sharing` |
| `sync_rest_chain` | `diagnose.py` — `_coupling_analysis` |
| `granular_decomposition` | `diagnose.py` — landscape manifest |
| Hypothesis confidence | `hypothesize.py`, `recommend.py` |
| Evidence confidence | `models.EvidenceItem.confidence` |

---

## Related

- [Operating model](operating-model.md)
- [Problem statement](problem-statement.md)
- [Current state architecture](current-state-architecture.md)
