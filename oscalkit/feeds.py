"""oscalkit.feeds — edge/air-gap data-feed integration for oscalkit.

Wires the bundled :mod:`oscalkit.datafeeds` ingestion engine (keyless HTTPS
fetch -> disk cache -> offline re-serve -> sneakernet snapshot) to the one
authoritative feed this compliance tool consumes:

    * ``oscal-800-53-rev5-catalog`` — the real NIST SP 800-53 rev5 control
      catalog, published by NIST as native OSCAL JSON at
      https://github.com/usnistgov/oscal-content

The catalog is used to resolve bare control ids (``ac-2``) to their official
control **titles** (``Account Management``) and **family** names, so that
``oscalkit controls``, ``coverage``, and ``stats`` emit human-readable,
audit-grade output instead of opaque ids.

Everything runs offline once cached: ``--offline`` serves the cache and never
touches the network, and the snapshot workflow tars the cache for transfer
into an air-gapped enclave. Defensive / authorized-use only.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from oscalkit import datafeeds

# Feeds relevant to oscalkit's compliance domain. The bundled catalog has 17
# feeds across many domains; oscalkit only consumes the OSCAL control catalog.
RELEVANT_FEED_IDS = ("oscal-800-53-rev5-catalog",)

# Family-code -> long name, derived from the SP 800-53 rev5 group titles. Used
# as a no-network fallback for `stats` family labels.
_FAMILY_FALLBACK = {
    "ac": "Access Control",
    "at": "Awareness and Training",
    "au": "Audit and Accountability",
    "ca": "Assessment, Authorization, and Monitoring",
    "cm": "Configuration Management",
    "cp": "Contingency Planning",
    "ia": "Identification and Authentication",
    "ir": "Incident Response",
    "ma": "Maintenance",
    "mp": "Media Protection",
    "pe": "Physical and Environmental Protection",
    "pl": "Planning",
    "pm": "Program Management",
    "ps": "Personnel Security",
    "pt": "PII Processing and Transparency",
    "ra": "Risk Assessment",
    "sa": "System and Services Acquisition",
    "sc": "System and Communications Protection",
    "si": "System and Information Integrity",
    "sr": "Supply Chain Risk Management",
}


def relevant_feeds() -> List[dict]:
    """The catalog entries oscalkit consumes (filtered to the compliance domain)."""
    catalog = datafeeds.load_catalog()
    by_id = {f["id"]: f for f in catalog.get("feeds", [])}
    return [by_id[fid] for fid in RELEVANT_FEED_IDS if fid in by_id]


def is_relevant(feed_id: str) -> bool:
    return feed_id in RELEVANT_FEED_IDS


def update(feed_id: str = "oscal-800-53-rev5-catalog"):
    """Fetch + cache a relevant feed. Raises on an irrelevant id."""
    if not is_relevant(feed_id):
        raise KeyError(
            f"{feed_id!r} is not an oscalkit feed; allowed: {', '.join(RELEVANT_FEED_IDS)}")
    return datafeeds.update(feed_id)


def get(feed_id: str = "oscal-800-53-rev5-catalog", *, offline: bool = False):
    """Return parsed feed content (online refresh unless ``offline``)."""
    if not is_relevant(feed_id):
        raise KeyError(
            f"{feed_id!r} is not an oscalkit feed; allowed: {', '.join(RELEVANT_FEED_IDS)}")
    return datafeeds.get(feed_id, offline=offline)


def _walk_controls(controls, fam_title, titles, families):
    for ctrl in controls or []:
        if not isinstance(ctrl, dict):
            continue
        cid = ctrl.get("id")
        if cid:
            cid = str(cid)
            titles[cid] = ctrl.get("title", "")
            families[cid] = fam_title
        # enhancements nest as controls[].controls[]
        if ctrl.get("controls"):
            _walk_controls(ctrl["controls"], fam_title, titles, families)


def title_index(*, offline: bool = False) -> Dict[str, Dict[str, str]]:
    """Flatten the NIST catalog feed to ``{control_id: {title, family}}``.

    Returns an empty dict if nothing is cached and ``offline`` (so callers can
    degrade gracefully to bare ids).
    """
    try:
        doc = get(offline=offline)
    except (FileNotFoundError, ConnectionError, KeyError):
        return {}
    catalog = doc.get("catalog", doc) if isinstance(doc, dict) else {}
    titles: Dict[str, str] = {}
    families: Dict[str, str] = {}
    for grp in catalog.get("groups", []) or []:
        fam_title = grp.get("title", grp.get("id", ""))
        _walk_controls(grp.get("controls", []), fam_title, titles, families)
    for grp in catalog.get("groups", []) or []:  # nested groups
        for sub in grp.get("groups", []) or []:
            _walk_controls(sub.get("controls", []), sub.get("title", ""), titles, families)
    return {cid: {"title": titles[cid], "family": families.get(cid, "")} for cid in titles}


def resolve_titles(control_ids, *, offline: bool = False) -> Dict[str, str]:
    """Map each control id to its official NIST title (or "" if unknown)."""
    idx = title_index(offline=offline)
    return {cid: idx.get(cid, {}).get("title", "") for cid in control_ids}


def family_name(code: str) -> str:
    """Long family name for a control-family code, from the catalog fallback."""
    return _FAMILY_FALLBACK.get(code.lower(), code.upper())
