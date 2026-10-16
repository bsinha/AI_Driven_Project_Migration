# Meeting Minutes — 1 September 2026

**Topic:** POC review and way forward (two parallel POCs)  
**Attendees (from transcript):** Saurabh Gupta, Vidyasagar Uddagiri, Bipul Sinha, Mphikeleli Zwane  
**Also referenced:** Ankur, Vian, Chris (upcoming presentation), ATM client (meeting 2 Sep)

---

## 1. Purpose

Review progress on POC work, clarify technical positioning (deterministic vs AI), strengthen the approach before customer-facing presentations, and align on timeline and resourcing.

---

## 2. Two POCs (do not merge)

| POC | Focus | Owner / track | This meeting emphasis |
|-----|-------|---------------|----------------------|
| **POC 1 — AI-assisted microservice migration** | Granular microservices → evidence → bounded contexts → governed migration | Bipul (+ GP support) | Architecture framework, complexities, upgraded deck |
| **POC 2 — ATM** | Reconciliation logic (stage-by-stage) | ATM / client track (Vidyasagar) | Client meeting 2 Sep; show approach in PPT before live app |

When Saurabh said **“both cases”** and **“ATM one also”**, he meant **two POCs**, not two scenarios inside the migration framework.

---

## 3. Key discussion points

### 3.1 Deterministic vs AI — terminology (Vidyasagar / Bipul)

**Vidyasagar’s question:** Architecture patterns come from a defined book of knowledge — AI should not invent outside that. Why call stages “non-deterministic”?

**Bipul’s clarification:**

- **Deterministic** = no LLM. Same codebase and documents → same output every run (discover, graph, diagnose).
- **AI-assisted** = LLM involved. Same prompt can yield different text — hence “non-deterministic” in the **repeatability** sense.

**Alignment needed for stakeholders:** Use three labels, not two:

| Label | Meaning |
|-------|---------|
| **Deterministic analysis** | Evidence, graph, smells — no LLM |
| **Pattern-constrained AI** | LLM reasons over evidence within architecture knowledge / patterns — not free-form design |
| **Human decision** | Gates, ADR approval, plan approval |

Pattern constraint and LLM repeatability are **different axes**. The deck should show both.

### 3.2 Complexity and “foolproof” positioning (Saurabh)

- Approach is **largely there**, but must **capture real-world complexities and exceptions** before claiming the method is robust enough for formal client use.
- Discuss complexities with **Ankur and Vian**; incorporate into an **upgraded presentation/document**.
- Goal: demonstrate how the framework **detects, reasons, and routes** edge cases through human decision — not automate every path.

### 3.3 Resourcing (Saurabh / Vidyasagar)

- Bipul is contributing **part-time** alongside another project.
- Assign **GP(s)** to support **execution** so Bipul is not the bottleneck.
- Bipul continues **solution / architecture thinking**; team executes implementation, deck updates, scenario validation.

### 3.4 Customer-facing story (Saurabh)

- Before customer meetings: **build and explain the logic in the PPT** — stage-by-stage flow.
- Customer may **not** see a live application; the presentation must stand alone.
- For ATM POC: show **how recon is proposed stage-by-stage** in slides.
- Share updated presentation with **Saurabh** when ready.

### 3.5 Timeline

- **By Friday (5 Sep):** Clear identified cases / complexities for internal readiness.
- **Following week:** Present to **Chris** (after internal sign-off with Saurabh).
- **2 Sep:** ATM client meeting — gather inputs; discuss further after.

---

## 4. Decisions

1. **Two POCs remain separate** — migration framework vs ATM recon.
2. **Friday internal target** for upgraded migration POC materials and complexity coverage.
3. **GP support** assigned to Bipul for execution (Vidyasagar to tag).
4. **PPT-first** customer narrative — full stage-by-stage story without requiring live demo.
5. **Internal review** with Saurabh before Chris presentation.

---

## 5. Action items

### POC 1 — AI-assisted microservice migration (this repository)

| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| A1 | Clarify **deterministic vs pattern-constrained AI vs human** in deck (three-way, not binary) | Bipul / Vidyasagar | Wed 3 Sep | Open |
| A2 | Complete **complexity / exception matrix** with detect → AI → human for each scenario | Bipul / Vidyasagar | Wed 3 Sep | In progress (`docs/migration-complexity-matrix.md`) |
| A3 | Document **iteration & re-entry** (reject hypothesis, re-diagnose, phase loop) | Bipul | Tue 3 Sep | Done (`docs/operating-model.md`) |
| A4 | Workshop with **Ankur & Vian** on complexity scenarios and narrative | Bipul, Vidyasagar | Wed 3 Sep | Open |
| A5 | **Upgrade stakeholder presentation** — iteration diagram, complexity slide, terminology fix | Bipul / Vidyasagar + GP | Thu 4 Sep | Open |
| A6 | **Friday dry-run** — EuroSA E2E, rejection path, gap honesty | Team | Fri 5 Sep | Open |
| A7 | Share updated PPT/deck with **Saurabh** for review | Vidyasagar | Fri 5 Sep | Open |
| A8 | Prepare **Chris presentation** (week of 8 Sep) after Saurabh approval | Vidyasagar / team | Mon 8 Sep | Open |
| A9 | Tag **GP(s)** for execution support (deck, scenarios, playbook tasks) | Vidyasagar | ASAP | Open |

### POC 2 — ATM (separate workstream)

| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| B1 | **Client meeting** — gather requirements / inputs | Vidyasagar / ATM team | Tue 2 Sep | Open |
| B2 | Build recon logic **stage-by-stage** for PPT (not app-first) | ATM team | Thu 4 Sep | Open |
| B3 | ATM slides: **how recon runs stage-by-stage** for customer | Vidyasagar | Fri 5 Sep | Open |
| B4 | Align ATM timeline with Friday “both cases” checkpoint | Vidyasagar / Saurabh | Fri 5 Sep | Open |

---

## 6. Risks / watch items

- **Terminology confusion** — “non-deterministic” read as “uncontrolled AI”; mitigate with pattern-constrained framing.
- **Scope creep** — avoid new UI/platform features before Friday; strengthen **story and exceptions**.
- **Single-person dependency** — mitigated by GP assignment.
- **Transcript gap** — middle session (complexity examples, iteration) may contain detail not captured in partial transcript; confirm with attendees.

---

## 7. Related repo artifacts

- [Operating model](operating-model.md)
- [Migration complexity matrix](migration-complexity-matrix.md)
- [Stakeholder presentation](stakeholder-presentation.md)
- [Framework methodology](framework-methodology.md)
