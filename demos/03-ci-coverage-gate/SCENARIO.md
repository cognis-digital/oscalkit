# Demo 03 — Fail a CI build when control coverage regresses

**Situation.** Project Falcon gates merges to `main` on coverage of its
MODERATE baseline. The SSP currently satisfies 12 of 15 controls; the team
wants the pipeline red until coverage reaches 95%.

**Files**

- `moderate-baseline.yaml` — the gating baseline (15 controls, 800-53 ids).
- `ssp.json` — the system security plan claiming 12 of them.

## Run it (the CI step)

```bash
python -m oscalkit coverage \
    demos/03-ci-coverage-gate/ssp.json \
    demos/03-ci-coverage-gate/moderate-baseline.yaml \
    --min-coverage 0.95
echo "exit code: $?"
```

## What you should see

Coverage is **80.0%** (12/15), missing **`cp-9`** (System Backup), **`ir-4`**
(Incident Handling), and **`si-2`** (Flaw Remediation). Because 0.80 < 0.95 the
command exits **1** — a failing CI step. Lower the gate to `--min-coverage 0.75`
and it exits **0**.

## Drop-in CI snippet

```yaml
# .github/workflows/compliance.yml
- name: OSCAL coverage gate
  run: |
    python -m oscalkit coverage ssp.json moderate-baseline.yaml \
      --min-coverage 0.95 --format md --out coverage.md
```

The `--format md --out` pair writes a Markdown gap table you can attach to the
PR or upload as a job artifact.
