# Demo 02 — NIST 800-53 LOW baseline gap audit for a SaaS

**Situation.** Acme Notes is a multi-tenant SaaS pursuing a Low-impact
authorization. Security publishes a component-definition listing the controls
the product implements; the assessor needs the gap against the 800-53 LOW
baseline before a formal review.

**Files**

- `catalog.json` — a subset of NIST SP 800-53 Rev 5 (AC/AU/IA/SI/RA families,
  control titles per the public 800-53 catalog).
- `low-baseline.json` — a profile selecting 13 of those controls as the LOW
  baseline.
- `saas-component.json` — the product's claimed controls (10 of the 13).

## Run it

```bash
python -m oscalkit validate demos/02-nist80053-low-gap/low-baseline.json
python -m oscalkit coverage \
    demos/02-nist80053-low-gap/saas-component.json \
    demos/02-nist80053-low-gap/low-baseline.json
```

## What you should see

Coverage is **76.9%** (10/13). The product is **missing `ac-8`** (System Use
Notification), **`au-6`** (Audit Review/Analysis/Reporting), and **`ra-5`**
(Vulnerability Monitoring and Scanning).

## How to act

Open POA&M items for `ac-8`, `au-6`, `ra-5`. Re-run after each lands; gate the
release pipeline with `--min-coverage 1.0` once you intend full LOW coverage.
