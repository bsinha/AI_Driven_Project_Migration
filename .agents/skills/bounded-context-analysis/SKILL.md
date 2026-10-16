---
name: bounded-context-analysis
description: Runs diagnose through recommend stages with evidence-backed bounded context discovery. Use for architecture health assessment, smell detection, or AI hypotheses.
---

# Bounded Context Analysis

1. Complete stages discover → ingest → graph first
2. Diagnose (deterministic): `run --stage diagnose` — coupling, smells, health report
3. Hypothesize: `run --stage hypothesize` — 2–4 candidate contexts (OpenAI or mock)
4. Recommend: `run --stage recommend` — ADRs + target architecture
5. Human gate: `approve --gate recommend` before plan

Never skip diagnose — LLM receives pre-computed metrics only.
