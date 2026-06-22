# Demo 08 — A clean component that passes a strict gate

**Situation.** The Edge Telemetry Agent has finished hardening and claims its
full baseline. You want to prove 100% coverage and a clean structural validation
so the strictest CI gate (`--min-coverage 1.0`) goes green.

**Files**

- `baseline.yaml` — a 5-control hardening baseline.
- `edge-agent.json` — the component implementing all 5.

## Run it

```bash
python -m oscalkit coverage \
    demos/08-full-coverage-pass/edge-agent.json \
    demos/08-full-coverage-pass/baseline.yaml --min-coverage 1.0
echo "exit: $?"

python -m oscalkit validate \
    demos/08-full-coverage-pass/edge-agent.json --format sarif
```

## What you should see

Coverage **100.0%** (5/5), no missing and no extra controls — the gate exits
**0**. The SARIF log has **0 results** (a clean run still emits a valid SARIF
file, so code scanning records the passing run).

## Why it matters

This is the "all green" reference: the shape a fully-implemented component and a
passing pipeline produce, so you can diff against it when something regresses.
