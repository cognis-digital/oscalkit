# oscalkit

**OSCAL compliance-as-code, with zero dependencies.** Validate, convert, and
diff control coverage for OSCAL catalogs, profiles, component definitions, and
system security plans — entirely with the Python standard library.

Part of the **Cognis Neural Suite**.

---

## Why now

OSCAL is the machine-readable format the U.S. government is standardizing on for
security documentation, and **as of 2026 FedRAMP requires machine-readable
(OSCAL) packages**. oscalkit lets teams lint those documents and prove control
coverage in CI — no heavyweight toolchain, no pip installs.

## Commands

```bash
# Structural + referential validation (required fields, ids, duplicates).
python -m oscalkit validate ssp.json
python -m oscalkit validate ssp.json --fail-on warning   # stricter gate
python -m oscalkit validate catalog.json --format sarif  # SARIF 2.1.0 for code scanning

# Convert between the two formats OSCAL ships in.
python -m oscalkit convert catalog.json --to yaml
python -m oscalkit convert profile.yaml --to json

# Flatten a document to the control ids it covers.
python -m oscalkit controls catalog.json

# Diff claimed controls against a baseline; gate on a minimum ratio.
python -m oscalkit coverage component-definition.json profile.yaml --min-coverage 0.8

# Run as a local MCP server (stdio JSON-RPC).
python -m oscalkit mcp
```

## Demos

Each `demos/<NN-name>/` folder holds real-shaped OSCAL inputs plus a
`SCENARIO.md` with the situation, the exact command, what to expect, and how to
act. Every demo is exercised by the test suite, so the outputs below are real.

| Demo | Scenario |
|------|----------|
| [01-basic](demos/01-basic/) | Validate + 75% coverage walk-through |
| [02-nist80053-low-gap](demos/02-nist80053-low-gap/) | 800-53 LOW baseline gap audit for a SaaS (76.9%) |
| [03-ci-coverage-gate](demos/03-ci-coverage-gate/) | Fail a CI build when coverage drops below a ratio |
| [04-sarif-code-scanning](demos/04-sarif-code-scanning/) | Surface findings in GitHub code scanning via SARIF 2.1.0 |
| [05-json-yaml-roundtrip](demos/05-json-yaml-roundtrip/) | Lossless JSON ⇄ YAML conversion |
| [06-merge-baselines](demos/06-merge-baselines/) | Merge LOW + MODERATE into one profile |
| [07-portfolio-stats](demos/07-portfolio-stats/) | Profile a catalog by control family |
| [08-full-coverage-pass](demos/08-full-coverage-pass/) | A clean component passing a strict 100% gate |

## Document classes understood

| Type                  | Validated for                                   |
|-----------------------|-------------------------------------------------|
| catalog               | groups/controls present, well-formed ids        |
| profile               | imports at least one source, selected ids       |
| component-definition  | components + implemented-requirements            |
| system-security-plan  | control-implementation + baseline import        |

## What sets oscalkit apart

- **Coverage diffing built in.** Not just a linter — it answers "what controls
  am I missing against this baseline?" and gates CI on a coverage ratio.
- **SARIF 2.1.0 output.** `validate --format sarif` emits the OASIS format
  GitHub code scanning / Azure DevOps ingest, so OSCAL findings land in the same
  Security tab as your SAST results (see [demo 04](demos/04-sarif-code-scanning/)).
- **Round-trippable JSON ⇄ YAML.** Teams mix both; oscalkit converts losslessly
  for the document shapes it handles.
- **MCP-native** (`validate` / `controls` / `coverage`) and an opt-in local-fleet
  AI hook (default OFF) that drafts remediation hints for missing controls.
- **Pure standard library.** Runs anywhere Python does, in an air-gap, offline.

## Tests

```bash
python -m pytest -q     # or: python -m unittest discover -s tests
```

## Interoperability

`oscalkit` composes with the 300+ tool Cognis suite — JSON in/out and a shared
OpenAI-compatible `/v1` backbone. See **[INTEROP.md](INTEROP.md)** for the
suite map, composition patterns, and reference stacks.

## Integrations

Forward `oscalkit`'s findings to STIX/MISP/Sigma/Splunk/Elastic/Slack/webhooks via
[`cognis-connect`](https://github.com/cognis-digital/cognis-connect). See **[INTEGRATIONS.md](INTEGRATIONS.md)**.

## License

Cognis Open Collaboration License (COCL) 1.0 — see [`LICENSE`](LICENSE).
© 2026 Cognis Digital LLC. Original Cognis work modeling the public OSCAL schema
shapes; no third-party code, names, or branding.

<!-- cognis:domains:start -->
## Domains

**Primary domain:** AI & ML  ·  **JTF MERIDIAN division:** ATHENA-PRIME · SAGE

**Topics:** `cognis` `ai` `llm` `machine-learning` `crypto` `web3`

Part of the **Cognis Neural Suite** — 300+ source-available tools organized across 12 domains under the JTF MERIDIAN command structure. See the [suite on GitHub](https://github.com/cognis-digital) and [jtf-meridian](https://github.com/cognis-digital/jtf-meridian) for how the pieces fit together.
<!-- cognis:domains:end -->

## Usage — step by step

`oscalkit` validates, converts, and diffs control coverage for OSCAL catalogs, profiles, component definitions, and SSPs.

1. **Install** (pure stdlib, Python 3.10+):
   ```bash
   pip install "git+https://github.com/cognis-digital/oscalkit.git"
   ```
2. **Validate** an OSCAL document (structural + referential checks); `--fail-on` sets the severity that trips a non-zero exit:
   ```bash
   oscalkit validate ssp.json --fail-on error
   ```
3. **Inspect** the controls a document covers, and summary stats by family:
   ```bash
   oscalkit controls ssp.json
   oscalkit stats catalog.json
   ```
4. **Diff coverage** of claimed controls vs a baseline, and gate on a ratio (`--format md` / `--out` for a report file):
   ```bash
   oscalkit coverage ssp.json baseline.json --min-coverage 0.9 --format md --out coverage.md
   ```
5. **Automate** — convert between JSON/YAML or merge baselines into one profile in a pipeline:
   ```bash
   oscalkit convert ssp.yaml --to json --out ssp.json
   oscalkit merge low.json moderate.json --to json --out profile.json
   ```
   Or run it as a local MCP server (stdio JSON-RPC): `oscalkit mcp`.
