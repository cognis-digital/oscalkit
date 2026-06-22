# Demo 05 — Convert OSCAL JSON <-> YAML (round-trippable)

**Situation.** Your assessors author component definitions in YAML (easier to
review in PRs), but your toolchain and FedRAMP submission expect JSON. You need
a lossless converter for the document shapes oscalkit handles — no PyYAML, no
external deps.

**File**

- `component.json` — a Payments Gateway component claiming `sc-8`, `sc-13`,
  `au-2`.

## Run it

```bash
# JSON -> YAML for human review
python -m oscalkit convert demos/05-json-yaml-roundtrip/component.json \
    --to yaml --out component.yaml

# YAML -> JSON for the pipeline
python -m oscalkit convert component.yaml --to json --out component.out.json
```

## What you should see

The YAML preserves the full structure (metadata, components, control
implementations). Converting back to JSON yields the same control-id set
(`au-2`, `sc-8`, `sc-13`) — verify with:

```bash
python -m oscalkit controls component.yaml
```

## Why it matters

Teams mix both formats. A dependency-free round-trip means the conversion can
run anywhere Python does, including air-gapped review environments, without a
supply-chain footprint.
