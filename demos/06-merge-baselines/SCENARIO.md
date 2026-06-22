# Demo 06 — Merge two baselines into one combined profile

**Situation.** An internal product must satisfy the *union* of your LOW and
MODERATE baselines (some teams pin LOW, a regulated tenant pins MODERATE). You
want a single merged profile to validate every component against.

**Files**

- `low.json` — LOW baseline (5 controls).
- `moderate.yaml` — MODERATE baseline (10 controls; overlaps LOW on ac-2/au-2/
  ia-2/si-4).

## Run it

```bash
python -m oscalkit merge \
    demos/06-merge-baselines/low.json \
    demos/06-merge-baselines/moderate.yaml \
    --to json --out merged-profile.json

python -m oscalkit controls merged-profile.json
python -m oscalkit validate merged-profile.json
```

## What you should see

The merged profile selects the **union of 11 controls**:
`ac-2, ac-3, ac-6, au-2, au-6, cm-6, cp-9, ia-2, ir-4, sc-7, si-4`. It validates
as a well-formed `profile` (PASS). Inputs may be JSON or YAML and are merged
deterministically (sorted, de-duplicated).

## How to act

Use `merged-profile.json` as the single baseline argument to `coverage` so each
component is measured against the combined requirement set.
