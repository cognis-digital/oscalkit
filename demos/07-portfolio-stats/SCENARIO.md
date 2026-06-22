# Demo 07 — Profile a control catalog by family

**Situation.** Before kicking off an assessment you want a quick shape-of-the-
work read on a catalog: how many controls, spread across which families. Feed
the JSON into a dashboard or a slide.

**File**

- `portfolio-catalog.json` — a 13-control catalog across AC/AU/SC/SI.

## Run it

```bash
python -m oscalkit stats demos/07-portfolio-stats/portfolio-catalog.json
python -m oscalkit stats demos/07-portfolio-stats/portfolio-catalog.json \
    --format json
```

## What you should see

13 controls across **4 families**: `ac` (5, including the `ac-2.1`
enhancement), `au` (2), `sc` (4), `si` (2). The JSON form is ready to pipe into
`jq` or a charting step:

```bash
python -m oscalkit stats portfolio-catalog.json --format json \
  | jq '.by_family'
```

## How to act

Families with the most controls (here `ac` and `sc`) usually carry the heaviest
evidence burden — staff and schedule the assessment accordingly.
