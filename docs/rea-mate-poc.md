# REA × MATE Proof of Concept

## Purpose

Evaluate whether [REA](https://github.com/morluto/rea) can contribute useful, additional evidence to MATE without replacing MATE's existing ingestion and analysis paths.

This is an experiment, not a commitment to a runtime dependency. MATE remains responsible for project lifecycle, evidence normalization and provenance, architecture graph construction, diagnosis, modernization decisions, and human approval gates.

## Guardrails

- Keep the existing Java 17 / Spring Boot `sample-bank` path as the regression baseline.
- Keep the MATE pipeline technology-agnostic; any integration emits MATE `EvidenceItem` values at the ingestion boundary.
- Do not make REA mandatory. Existing analysis must continue when REA is absent or disabled.
- Do not infer that an empty result means a fact is absent. Represent unknown, unsupported, failed, and incomplete coverage distinctly from a confirmed empty result.
- Preserve source identity/fingerprint, provider and provider record ID, collection time, scope, coverage status, limitations, and a pointer or digest for the raw REA output.
- Do not allow REA findings to bypass MATE's diagnosis/recommendation/plan approval gates or trigger automatic migration changes.
- Start with offline artifacts/captures; do not run untrusted binaries or active runtime/network collection as part of the first test.

## Initial capability hypothesis

REA is not a replacement for MATE's Java/Spring static ingestion. The first useful test should target evidence MATE does not already capture well. A small, sanitized HTTP capture (HAR/SAZ, if supported by the installed REA version) is a candidate because it can expose observed request/response paths and interaction sequences. It only demonstrates incremental value if the capture can be tied to known sample-bank services and MATE can distinguish observed traffic from inferred or unobserved behavior.

If the current REA build cannot reliably parse a suitable offline capture, record that as a result and choose another explicitly supported artifact. Do not invent a REA output schema or couple MATE to undocumented internals.

## Experiment plan

### 1. Baseline

- Inspect the current ingestion adapters, `EvidenceItem` contract, graph mapping, and tests under `platform/migrate_framework/`.
- Run the existing tests and record the command, result, and environment.
- Select a small, representative set of sample-bank services and document evidence already produced by MATE.

### 2. Independent REA run

- Verify the REA version, installation requirements, supported input format, and license/dependency constraints.
- Use one sanitized, offline input only.
- Save the original input fingerprint and complete REA output as experiment artifacts outside production project data.
- Record observed coverage, limitations, failures, runtime, and resource use.

### 3. Evidence comparison

For each candidate fact, classify it as:
- already known by MATE;
- genuinely additional evidence;
- duplicate or conflicting evidence;
- unknown / not observed;
- unsupported or incomplete.

Do not count an output as incremental value solely because its wording differs from an existing fact.

### 4. Optional adapter

Only after inspecting the real REA output contract, implement a small opt-in adapter in the existing platform structure. Normalize into the current `EvidenceItem` contract without changing the core pipeline or introducing a hard dependency on REA.

The adapter should preserve raw-output provenance and use stable, deterministic identity for repeat ingestion. Conflicting observations must remain visible rather than silently overwrite one another.

### 5. Validation

- Unit-test normalization, provenance, coverage states, malformed output, and unsupported input.
- Test repeat ingestion for deterministic IDs and duplicate handling.
- Test that disabled/unavailable REA leaves the current pipeline unchanged.
- Compare graph/diagnosis behavior with baseline evidence versus baseline plus REA evidence.
- Re-run the existing regression suite and report any differences.

## Acceptance criteria

The POC succeeds only if all applicable criteria are met:

1. A supported, offline REA input can be processed reproducibly.
2. At least one useful evidence item is demonstrably additional to MATE's baseline, or the experiment clearly documents why no incremental value was found.
3. Evidence records preserve provenance and distinguish empty, unknown, failed, unsupported, and partial coverage where the source permits.
4. Repeat ingestion does not create uncontrolled duplicates.
5. REA is optional and the existing Java/Spring workflow and human approval gates remain intact.
6. Tests and limitations are reported honestly; no unexecuted test is described as passing.

## Out of scope

- Replacing MATE's current Java/Spring ingestion.
- Making REA a required service or runtime dependency.
- Broad multi-language integration.
- Active probing, browser automation, binary execution, or production traffic capture.
- Autonomous modernization, automatic code changes, or bypassing human approval.

## Current status

- [x] Dedicated POC branch created from `switch_to_codex`.
- [ ] Inspect current adapter and evidence contracts.
- [ ] Record baseline test results.
- [ ] Verify REA installation and actual output schema.
- [ ] Select and run one offline evidence experiment.
- [ ] Decide whether a minimal adapter is justified.
