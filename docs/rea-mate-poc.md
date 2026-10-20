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

## Initial repository inspection findings

The following were confirmed during the initial inspection, before adapter implementation.

- The sample bank has 16 granular Spring Boot services and a landscape manifest. The customer identity service includes an OpenAPI specification, and MATE's existing OpenAPI adapter already extracts service and endpoint evidence from such files.
- MATE's current `TraceAdapter` reads `application.yml` / `application.yaml` downstream configuration. Despite the `trace_span` evidence type and tags, this is configured dependency evidence, not a record of actual observed runtime calls.
- The repository also contains `metadata/traces/payment-flow.json`, a synthetic payment-flow trace with a seven-hop synchronous chain. Therefore, a new REA result must be compared against both existing static evidence and this synthetic trace; a larger evidence count alone is not proof of value.
- The current `EvidenceItem` model has flexible `attributes`, `relations`, and `tags`, but no first-class coverage/provenance fields. The initial adapter should carry REA-specific provenance and coverage in a documented attributes envelope rather than expand the core model prematurely.
- REA documents offline HAR 1.2 and SAZ inspection via `inspect-web-network-capture`. Its CLI can emit JSON. This confirms a candidate workflow, not that a suitable capture has been processed or that the actual JSON contract has been validated against a sample.
- REA's current package metadata identifies version 6.7.0 and requires Node.js `^22.19.0 || ^24.11.0 || >=26.0.0`. Verify the local runtime before attempting the run; do not assume an older Node 22 release is sufficient.
- The MATE baseline test command in the repository's Makefile is `make test` (which runs `cd platform && pytest -v`).

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
- [x] Run the MATE test suite using the Makefile's underlying pytest command.
- [x] Verify the local Node runtime and whether a REA CLI is installed.
- [x] Implement an opt-in file-based adapter against the published REA 6.7.0 Evidence contract, with a clearly labelled documented-shape fixture.
- [x] Correct configured `application.yml` dependencies so they are not reported as observed runtime traces.
- [ ] Validate the adapter against output from a locally installed REA CLI.
- [ ] Obtain and run one sanitized offline sample-bank capture.
- [ ] Compare live REA findings with static and synthetic-trace baseline evidence.

## Implementation and validation status (2026-10-20)

### Adapter and data flow

`ReaCaptureAdapter` is registered but inactive unless `MATE_REA_EVIDENCE_PATH` names a saved REA JSON Evidence file. It does not invoke or depend on REA. The first adapter contract supports HAR inspection Evidence only (REA's `parameters.format` must be `har`); it validates the operation, evidence identity, capture digest and records, then emits:

- one `network_capture` item with the artifact digest, record counts, selected/all-record scope, REA evidence ID, provider coverage and limitations;
- one `api_endpoint` item per usable HTTP request record, carrying method, sanitized path, destination, optional response status/MIME type and record provenance.

Request/response headers, cookies, URL query values, fragments, request bodies and response bodies are not copied. Numeric, UUID and high-entropy path segments are redacted. When a destination port matches a service port in `landscape-manifest.yaml`, the endpoint is associated with that service and relates via `exposes`. A captured destination alone never creates a caller-to-service `calls`/`depends_on` relationship. IDs are stable for the same capture digest and producer ordinal. Empty captures still emit a capture record with zero usable requests.

The provider adds no Python or Node dependency and leaves ordinary ingest unchanged when the environment variable is unset. Existing required approval gates are unchanged. `network_capture` is in the evidence schema and graph metadata is excluded from service nodes.

The existing `TraceAdapter` reads configured downstream URLs from `application.yml`. It now tags those records as `configured`, and the ingest readiness report no longer treats them as observed runtime traces. Its prior `trace_span` evidence type remains for compatibility; REA observations use `api_endpoint` with `observed` and `network_capture` tags.

### REA runtime and input contract

The local runtime is Python 3.13.1 and Node.js 24.20.0. The `rea` CLI is not installed. REA's published package metadata reports `rea-agents` 6.7.0 and Node `^22.19.0 || ^24.11.0 || >=26.0.0`; the local Node version is compatible. This is a published-version check, not a locally installed REA version check. REA documents `inspect-web-network-capture` as offline, supports HAR 1.2, returns portable Evidence JSON with `evidence_id` and `normalized_result`, and identifies capture artifacts by SHA-256. See [REA's capture documentation](https://github.com/morluto/rea/blob/main/docs/web-network-captures.md), [REA's MCP Evidence contract](https://github.com/morluto/rea/blob/main/docs/mcp-contracts.md), and [REA package metadata](https://github.com/morluto/rea/blob/main/package.json).

No HAR or SAZ file was present and no real REA output was generated. The checked-in `platform/tests/fixtures/rea_har_evidence.documented-shape.example.json` is explicitly a representative documented-shape fixture; it is not a HAR capture or a real REA response. Its test validates the parser contract and does not establish live compatibility. On a host with compatible Node and REA available, verify its CLI with `rea --help`, then inspect a real sanitized capture using:

```powershell
$reaOutput = npx --yes rea-agents@6.7.0 inspect-web-network-capture C:\absolute\sample-bank.har har --json
[System.IO.File]::WriteAllText('C:\absolute\rea-output.json', ($reaOutput -join "`n"), [System.Text.UTF8Encoding]::new($false))
```

Use a controlled, non-production run. The sample-bank controllers currently expose placeholder endpoints and do not execute their configured downstream calls, so this sample cannot currently demonstrate the seven-hop payment path. Fiddler Everywhere can export a session as HTTP Archive; confirm `log.version` is `"1.2"`, remove credentials and customer data, and retain the sanitized capture's SHA-256. REA's command reads the saved capture and does not fetch URLs or start a listener.

To enable import in PowerShell, set `$env:MATE_REA_EVIDENCE_PATH` to the saved REA JSON output before running MATE ingest. Initialize/discover the sample project, then run its `ingest` stage. The adapter is not activated when the variable is unset. Keep the normal ingest-gate review before running graph or later stages.

Example using the repository CLI from `platform/` (use the project ID printed by `init`):

```powershell
$env:MATE_REA_EVIDENCE_PATH = 'C:\absolute\rea-output.json'
python -m migrate_framework.cli init --name 'EuroSA Bank REA POC' --source '..\sample-bank' --landscape '..\sample-bank\landscape-manifest.yaml'
python -m migrate_framework.cli run --project-id '<project-id>' --stage discover
python -m migrate_framework.cli run --project-id '<project-id>' --stage ingest
```

The ingest stage writes both the ordinary MATE evidence and REA-derived items to its normal evidence artifact. Inspect `source`, `tags`, and `attributes.rea` to distinguish OpenAPI declarations, configured dependencies, observed request records, and synthetic metadata. Do not use `--through` or `--auto-approve` to skip required human gates.

### Evidence comparison and limitations

The manifest contains 16 granular services. MATE's OpenAPI adapter finds 16 granular-service specs and 51 declared operations (plus one target-context spec with three operations). The configuration adapter emits 20 downstream dependency pairs. `payment-flow.json` lists eight service spans and declares seven synchronous hops. These are separate baselines: OpenAPI is declared surface, `application.yml` is configured dependency evidence, and the payment flow is synthetic.

The parser fixture contains one representative request to payment initiation. That endpoint and method are already declared by its OpenAPI file, so the fixture adds no demonstrated new endpoint. A real inspection could add observed request/status/timing evidence and corroborate a destination service, but cannot establish the complete runtime dependency graph. No live service/endpoint/relationship counts or unique/corroborated relationship counts are reported because no real capture has been inspected.

### Tests

The original `make test` command could not start because `make` is not installed in this PowerShell environment. The post-change suite ran as `python -m pytest -q --basetemp=.pytest-tmp` from `platform/`; the initial failures were due to missing declared Plotly and the sandbox's non-writable redirected Windows temp directory. Plotly 7.1.0 was installed in the user Python environment, and pytest used a workspace-local temp directory. Final result: **99 passed, 3 skipped** (102 collected, 4.29 seconds). The three skipped tests are existing tests guarded by their optional browser/graph capabilities.
