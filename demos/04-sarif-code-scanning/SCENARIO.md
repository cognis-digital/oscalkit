# Demo 04 — Surface OSCAL findings in GitHub code scanning (SARIF)

**Situation.** A contributor opens a PR that edits the control catalog. You
want oscalkit's structural findings to appear in the repository's **Security >
Code scanning** tab next to your SAST results — not buried in CI logs.

oscalkit emits **SARIF 2.1.0** (the OASIS format GitHub, Azure DevOps, and most
dashboards ingest) with `validate --format sarif`.

**File**

- `broken-catalog.json` — a catalog with four deliberate problems: a missing
  `metadata.title`, a malformed `uuid`, a duplicate `ac-2`, and a
  non-conforming control id.

## Run it

```bash
python -m oscalkit validate \
    demos/04-sarif-code-scanning/broken-catalog.json --format sarif \
    --out oscal-findings.sarif
```

## What you should see

A SARIF log with **4 results** and a rules catalog. Severities map to SARIF
levels: `error` (missing title) -> `error`, malformed uuid + duplicate id ->
`warning`, non-conforming id -> `note`. The plain `validate` (table) form exits
**1** because of the one error.

## Upload to GitHub code scanning

```yaml
# .github/workflows/oscal.yml
- run: python -m oscalkit validate catalog.json --format sarif --out oscal.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: oscal.sarif
```

Each finding becomes an annotation on the offending document, with the rule id
(`metadata.title`, `control.duplicate`, ...) carried through for triage.
