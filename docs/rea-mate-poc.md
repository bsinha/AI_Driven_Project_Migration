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

## Repository inspection findings

The following have been confirmed by inspecting the repository and REA's published documentation; no code has been executed as part of this inspection.

- The sample bank has 16 granular Spring Boot services and a landscape manifest. The customer identity service includes an OpenAPI specification, and MATE's existing OpenAPI adapter already extracts service and endpoint evidence from such files.
- MATE's current `TraceAdapter` reads `application.yml` / `application.yaml` downstream configuration. Despite the `trace_span` evidence type and tags, this is configured dependency evidence, not a record of actual observed runtime calls.
- The repository also contains `metadata/traces/payment-flow.json`, a synthetic payment-flow trace with a seven-hop synchronous chain. Therefore, a new REA result must be compared against both existing static evidence and this synthetic trace; a larger evidence count alone is not proof of value.
- The current `EvidenceItem` model has flexible `attributes`, `relations`, and `tags`, but no first-class coverage/provenance fields. The initial adapter should carry REA-specific provenance and coverage in a documented attributes envelope rather than expand the core model prematurely.
- REA documents offline HAR 1.2 and SAZ inspection via `inspect-web-network-capture`. Its CLI can emit JSON. This confirms a candidate workflow, not that a suitable capture has been processed or that the actual JSON contract has been validated against a sample.
- REA's current package metadata identifies version 6.7.0 and requires Node.js `^22.19.0 || ^24.11.0 || >=26.0.0`. Verify the local runtime before attempting the run; do not assume an older Node 22 release is sufficient.
- The MATE baseline test command in the repository's Makefile is `make test` (which runs `cd platform && pytest -v`). This command has **not** been run in this environment, so there is no baseline pass/fail result yet.

## Experiment plan

### 1. Baseline

- Inspect the current ingestion adapters, `EvidenceItem` contract, graph mapping, and tests under `platform/migrate_framework/`.
- Run `make test` from the repository root in a local checkout and record the command, result, and environment.
- Select a small, representative set of sample-bank services and document evidence already produced by MATE. The payment flow is a useful comparison case because the repository already has a synthetic reference trace.

### 2. Independent REA run

- Verify the installed REA version, Node.js version, installation requirements, and license/dependency constraints.
- Obtain a sanitized HAR 1.2 capture from a controlled, non-production sample-bank run. Label it as a test capture and retain its fingerprint. Do not represent the repository's synthetic trace JSON as a HAR or as real observed traffic.
- Run REA's documented offline capture inspection, for example:
  ```bash
  rea inspect-web-network-capture /absolute/path/to/sample-bank.har har --json > rea-capture-evidence.json
  ```
- Save the complete REA output as an experiment artifact outside production project data.
- Record observed coverage, limitations, failures, runtime, and resource use. Confirm the output schema from the actual output before writing any parser.

### 3. Evidence comparison

For each candidate fact, classify it as:
- already known by MATE from source/configuration;
- already represented by the synthetic metadata trace;
- genuinely additional observed evidence;
- duplicate or conflicting evidence;
- unknown / not observed;
- unsupported or incomplete.

Do not count an output as incremental value solely because its wording differs from an existing fact. A runtime observation should be labelled as such and must not be generalized to unobserved paths.

### 4. Optional adapter

Only after inspecting the real REA output contract, implement a small opt-in adapter in the existing platform structure. Prefer importing a saved REA JSON artifact over invoking REA from inside MATE. Normalize into the current `EvidenceItem` contract without changing the core pipeline or introducing a hard dependency on REA.

The adapter should preserve raw-output provenance and use stable, deterministic identity for repeat ingestion. Conflicting observations must remain visible rather than silently overwrite one another. Keep the adapter disabled by default and do not add it to the always-on default registry until its opt-in behavior is explicitly designed and tested.

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
- [x] Inspect current adapter and evidence contracts.
- [x] Inspect REA's documented offline capture workflow and declared runtime requirement.
- [ ] Run MATE baseline tests in a local checkout.
- [ ] Verify local REA installation/runtime and actual output schema.
- [ ] Obtain and run one sanitized offline sample-bank capture.
- [ ] Compare REA findings with static and synthetic-trace baseline evidence.
- [ ] Decide whether a minimal opt-in adapter is justified.
