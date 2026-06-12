# Demo 01 — Validate OSCAL and measure control coverage

This scenario uses three small OSCAL documents:

- `catalog.json` — a 5-control demo catalog (Access Control + Integrity)
- `profile.yaml` — a 4-control "low" baseline importing the catalog
- `component-definition.json` — a product claiming 3 of those controls

## Run it

```bash
# Structural + referential validation (catalog/profile/component/SSP).
python -m oscalkit validate demos/01-basic/catalog.json
python -m oscalkit validate demos/01-basic/profile.yaml

# Flatten any document to the set of control ids it covers.
python -m oscalkit controls demos/01-basic/catalog.json

# Diff what the product claims against the baseline.
python -m oscalkit coverage demos/01-basic/component-definition.json \
    demos/01-basic/profile.yaml

# Convert between the two formats OSCAL ships in.
python -m oscalkit convert demos/01-basic/catalog.json --to yaml
```

## What you should see

`coverage` reports **75%** — the component implements `ac-1`, `ac-2`, `si-4`
but is **missing `ra-5`** (Vulnerability Monitoring). Gate a pipeline with
`--min-coverage 0.8` to fail builds that drop below a threshold.

## Why it matters

As of 2026 FedRAMP requires machine-readable (OSCAL) packages. oscalkit gives
teams a dependency-free way to lint those documents and prove control coverage
in CI — long before a formal assessment.
