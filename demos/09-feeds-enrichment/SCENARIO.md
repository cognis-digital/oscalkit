# Demo 09 — NIST 800-53 rev5 feed enrichment (edge / air-gap)

oscalkit ships an edge-deployable data-feed layer that ingests the **real**
NIST SP 800-53 rev5 control catalog (published by NIST as native OSCAL JSON)
and uses it to resolve bare control ids to their official control **titles**.

Source feed (keyless, public):
`oscal-800-53-rev5-catalog` →
https://github.com/usnistgov/oscal-content/blob/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json

## 1. List the feed(s) this tool consumes

```
oscalkit feeds list
```

## 2. Fetch + cache the catalog once (online)

```
oscalkit feeds update oscal-800-53-rev5-catalog
```

The catalog is cached under `COGNIS_FEEDS_CACHE` (default `~/.cache/cognis-feeds`).

## 3. Enrich control output — works fully offline once cached

```
oscalkit controls catalog.json --enrich --offline
```

Instead of `ac-1, ac-2, ac-2.1 …` you get:

```
  ac-1       Policy and Procedures
  ac-2       Account Management
  ac-2.1     Automated System Account Management
```

`coverage --enrich` annotates every **missing** control with its official
NIST title, so a gap report reads like an auditor's worklist:

```
oscalkit coverage saas-component.json low-baseline.json --enrich --offline --format md
```

## 4. Air-gap transfer (sneakernet)

On a connected host, snapshot the cache; carry the tarball to the enclave:

```
oscalkit feeds update                       # connected host
oscalkit feeds snapshot-export feeds.tar.gz # -> removable media
# ... on the air-gapped host ...
oscalkit feeds snapshot-import feeds.tar.gz
oscalkit controls catalog.json --enrich --offline   # no network, full titles
```

The trimmed catalog used by the test suite lives at
`tests/fixtures/feeds-cache/` and demonstrates the same offline path with zero
network.
