# oscalkit — Usage Guide

oscalkit validates, converts, and measures coverage for OSCAL documents
(catalogs, profiles, component definitions, SSPs) — dependency-free.

## Commands

### validate
```bash
python -m oscalkit validate ssp.json
python -m oscalkit validate ssp.json --fail-on warning   # stricter CI gate
```

### convert (JSON ⇄ YAML)
```bash
python -m oscalkit convert catalog.json --to yaml
python -m oscalkit convert profile.yaml --to json
```

### controls / stats
```bash
python -m oscalkit controls catalog.json          # the control id set
python -m oscalkit stats catalog.json             # counts by control family
```
`stats` example output:
```
oscalkit stats — catalog
  controls : 5   families: 3
    ac     3
    ra     1
    si     1
```

### coverage (with Markdown gap report)
```bash
python -m oscalkit coverage component-definition.json profile.yaml
python -m oscalkit coverage component-definition.json profile.yaml \
    --format md --out GAP_REPORT.md        # audit-ready Markdown
python -m oscalkit coverage component-definition.json profile.yaml \
    --min-coverage 0.8                     # exit non-zero below threshold
```
The `md` format emits a table of missing controls and any extras — drop it into
a PR description or compliance ticket.

### merge baselines
```bash
python -m oscalkit merge low.json moderate.json --to json --out combined.json
```
Produces a profile selecting the **union** of all input control ids — useful for
"our system must satisfy baseline A *and* B".

## Document classes

| Type                 | Validated for                                |
|----------------------|----------------------------------------------|
| catalog              | groups/controls present, well-formed ids     |
| profile              | imports ≥ 1 source, selected ids             |
| component-definition | components + implemented-requirements        |
| system-security-plan | control-implementation + baseline import     |

## MCP server

```bash
python -m oscalkit mcp   # validate / controls / coverage over stdio JSON-RPC
```

## Why now

As of 2026, FedRAMP requires machine-readable (OSCAL) packages. oscalkit lets
teams lint those documents and prove control coverage in CI long before a formal
assessment — with a Markdown gap report you can attach to the audit trail.
