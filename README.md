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
