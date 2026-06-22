"""Core engine for oscalkit — OSCAL compliance-as-code toolkit.

OSCAL (the Open Security Controls Assessment Language) is the machine-readable
format the U.S. government is standardizing on for security documentation. As of
2026, FedRAMP requires machine-readable (OSCAL) packages — which makes a small,
dependency-free validator/converter genuinely useful to a lot of teams.

oscalkit works on the four document classes most people touch:

  * catalog              — a set of controls (e.g. NIST 800-53)
  * profile              — a baseline that imports + tailors a catalog
  * component-definition — what a product implements, per control
  * ssp (system-security-plan) — how a system satisfies a baseline

It does four things, all with the Python standard library:

  * validate  — structural + referential checks (required fields, well-formed
                identifiers, internal cross-references, duplicate IDs)
  * convert   — JSON <-> a YAML subset (round-trippable), since OSCAL ships in
                both and teams mix them
  * controls  — flatten a catalog/profile/component-definition to the set of
                control IDs it covers
  * coverage  — diff the controls a component/SSP claims against a baseline and
                report what's covered, missing, or extra

This is original Cognis Digital work modeling the public OSCAL schema shapes; it
contains no third-party code, names, or branding.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

TOOL_NAME = "oscalkit"
TOOL_VERSION = "0.1.0"

# The OSCAL document "root" keys we understand.
ROOT_TYPES = ("catalog", "profile", "component-definition",
              "system-security-plan", "ssp", "assessment-plan")

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}

# A loose OSCAL control-id shape, e.g. ac-1, ac-2.1, si-4, ra-5.
_CONTROL_ID_RE = re.compile(r"^[a-z]{2}-\d+(?:\.\d+)?$")
# UUID v4-ish.
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class OscalError(Exception):
    """User-facing OSCAL load/parse problem."""


@dataclass
class Finding:
    severity: str
    rule: str
    message: str
    location: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"severity": self.severity, "rule": self.rule,
                "message": self.message, "location": self.location}


@dataclass
class ValidationResult:
    doc_type: str
    source: str
    findings: List[Finding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def ok(self) -> bool:
        return self.errors == 0

    def to_dict(self) -> Dict[str, Any]:
        return {"doc_type": self.doc_type, "source": self.source,
                "ok": self.ok, "error_count": self.errors,
                "findings": [f.to_dict() for f in self.findings]}


# --------------------------------------------------------------------------- #
# YAML subset (round-trippable with JSON)
# --------------------------------------------------------------------------- #

def _coerce(text: str) -> Any:
    s = text.strip()
    if s in ("", "~", "null"):
        return None
    if s in ("true", "false"):
        return s == "true"
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def parse_yaml_subset(text: str) -> Any:
    """Parse a YAML subset (mappings, lists, scalars) into Python data."""
    lines = text.replace("\t", "  ").splitlines()
    toks: List[Tuple[int, str]] = []
    for raw in lines:
        # strip simple comments not inside quotes
        out, sgl, dbl = [], False, False
        for i, ch in enumerate(raw):
            if ch == "'" and not dbl:
                sgl = not sgl
            elif ch == '"' and not sgl:
                dbl = not dbl
            elif ch == "#" and not sgl and not dbl and (i == 0 or raw[i-1] in " \t"):
                break
            out.append(ch)
        line = "".join(out).rstrip()
        if not line.strip() or line.strip() == "---":
            continue
        indent = len(line) - len(line.lstrip(" "))
        toks.append((indent, line.strip()))
    if not toks:
        return {}
    pos = [0]

    def kv(s: str) -> Tuple[str, str]:
        i = s.find(":")
        if i == -1:
            return s, ""
        k, v = s[:i].strip(), s[i+1:].strip()
        if len(k) >= 2 and k[0] == k[-1] and k[0] in "\"'":
            k = k[1:-1]
        return k, v

    def parse_block(indent: int) -> Any:
        if pos[0] >= len(toks):
            return None
        cur, content = toks[pos[0]]
        if content.startswith("- "):
            return parse_list(indent)
        return parse_map(indent)

    def parse_list(indent: int) -> List[Any]:
        items: List[Any] = []
        while pos[0] < len(toks):
            cur, content = toks[pos[0]]
            if cur != indent or not content.startswith("- "):
                break
            inner = content[2:].strip()
            pos[0] += 1
            if ":" in inner and not (inner.find(":")+1 < len(inner)
                                     and inner[inner.find(":")+1] != " "):
                k, v = kv(inner)
                obj: Dict[str, Any] = {}
                obj[k] = _coerce(v) if v else _child(indent + 2)
                obj.update(cont_map(indent + 2))
                items.append(obj)
            elif inner == "":
                items.append(_child(indent + 2))
            else:
                items.append(_coerce(inner))
        return items

    def cont_map(indent: int) -> Dict[str, Any]:
        obj: Dict[str, Any] = {}
        while pos[0] < len(toks):
            cur, content = toks[pos[0]]
            if cur != indent or content.startswith("- "):
                break
            k, v = kv(content)
            pos[0] += 1
            obj[k] = _coerce(v) if v else _child(indent + 2)
        return obj

    def parse_map(indent: int) -> Dict[str, Any]:
        obj: Dict[str, Any] = {}
        while pos[0] < len(toks):
            cur, content = toks[pos[0]]
            if cur != indent or content.startswith("- "):
                break
            k, v = kv(content)
            pos[0] += 1
            obj[k] = _coerce(v) if v else _child(indent + 1)
        return obj

    def _child(min_indent: int) -> Any:
        if pos[0] >= len(toks):
            return None
        cur, content = toks[pos[0]]
        if cur < min_indent:
            return None
        return parse_list(cur) if content.startswith("- ") else parse_map(cur)

    result = parse_block(0)
    return result if result is not None else {}


def to_yaml(data: Any, indent: int = 0) -> str:
    """Serialize Python data to the YAML subset (round-trips parse_yaml_subset)."""
    sp = "  " * indent
    lines: List[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{sp}{k}:")
                lines.append(to_yaml(v, indent + 1))
            else:
                lines.append(f"{sp}{k}: {_scalar(v)}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item:
                inner = to_yaml(item, indent + 1).splitlines()
                if inner:
                    first = inner[0].lstrip()
                    lines.append(f"{sp}- {first}")
                    lines.extend(inner[1:])
            elif isinstance(item, list) and item:
                lines.append(f"{sp}-")
                lines.append(to_yaml(item, indent + 1))
            else:
                lines.append(f"{sp}- {_scalar(item)}")
    else:
        lines.append(f"{sp}{_scalar(data)}")
    return "\n".join(l for l in lines if l.strip() or l == "")


def _scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "" or any(c in s for c in ":#") or s.strip() != s:
        return '"' + s.replace('"', '\\"') + '"'
    return s


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #

def load(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise OscalError(f"file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".json":
            data = json.loads(text)
        elif ext in (".yaml", ".yml"):
            data = parse_yaml_subset(text)
        else:
            data = json.loads(text) if text.lstrip()[:1] in "{[" else parse_yaml_subset(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise OscalError(f"could not parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise OscalError("OSCAL document root must be an object")
    return data


def doc_type(doc: Dict[str, Any]) -> str:
    for t in ROOT_TYPES:
        if t in doc:
            return "system-security-plan" if t == "ssp" else t
    # Some files wrap under no root key; sniff by presence of known fields.
    return "unknown"


def _root(doc: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    t = doc_type(doc)
    key = "ssp" if (t == "system-security-plan" and "ssp" in doc) else t
    if key in doc and isinstance(doc[key], dict):
        return t, doc[key]
    return t, doc


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #

def validate(doc: Dict[str, Any], source: str = "<doc>") -> ValidationResult:
    t = doc_type(doc)
    res = ValidationResult(doc_type=t, source=source)

    if t == "unknown":
        res.findings.append(Finding("error", "root.unknown",
                                    "no recognized OSCAL root "
                                    f"({', '.join(ROOT_TYPES)})"))
        return res

    _t, root = _root(doc)

    # Common: metadata block with title + a uuid.
    md = root.get("metadata")
    if not isinstance(md, dict):
        res.findings.append(Finding("error", "metadata.missing",
                                    "missing or malformed `metadata`", t))
    else:
        if not md.get("title"):
            res.findings.append(Finding("error", "metadata.title",
                                        "metadata.title is required", t + ".metadata"))
        if not md.get("version"):
            res.findings.append(Finding("warning", "metadata.version",
                                        "metadata.version is recommended",
                                        t + ".metadata"))
    uuid = root.get("uuid")
    if not uuid:
        res.findings.append(Finding("error", "uuid.missing",
                                    f"{t}.uuid is required", t))
    elif not _UUID_RE.match(str(uuid)):
        res.findings.append(Finding("warning", "uuid.format",
                                    f"{t}.uuid does not look like a UUID: {uuid}", t))

    # Type-specific structure + collect ids for duplicate detection.
    ids = _collect_control_ids(t, root)
    seen: Set[str] = set()
    for cid, loc in ids:
        if not _CONTROL_ID_RE.match(cid):
            res.findings.append(Finding("info", "control.id_format",
                                        f"control id '{cid}' is unusual", loc))
        if cid in seen:
            res.findings.append(Finding("warning", "control.duplicate",
                                        f"duplicate control id '{cid}'", loc))
        seen.add(cid)

    if t == "catalog" and not root.get("groups") and not root.get("controls"):
        res.findings.append(Finding("error", "catalog.empty",
                                    "catalog has no groups or controls", t))
    if t == "profile":
        imports = root.get("imports")
        if not imports:
            res.findings.append(Finding("error", "profile.no_imports",
                                        "profile must import at least one source", t))
    if t == "component-definition":
        comps = root.get("components")
        if not comps:
            res.findings.append(Finding("error", "component-definition.empty",
                                        "no components defined", t))
    if t == "system-security-plan":
        if not root.get("control-implementation"):
            res.findings.append(Finding("error", "ssp.no_impl",
                                        "ssp has no control-implementation", t))
        if not root.get("import-profile"):
            res.findings.append(Finding("warning", "ssp.no_baseline",
                                        "ssp does not import a profile/baseline", t))
    return res


def _collect_control_ids(t: str, root: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return (control_id, location) for whatever this doc references/defines."""
    out: List[Tuple[str, str]] = []

    if t == "catalog":
        def walk_group(g: Dict[str, Any], path: str) -> None:
            for ctrl in g.get("controls", []) or []:
                if isinstance(ctrl, dict) and ctrl.get("id"):
                    out.append((str(ctrl["id"]), path))
            for sub in g.get("groups", []) or []:
                walk_group(sub, path)
        for ctrl in root.get("controls", []) or []:
            if isinstance(ctrl, dict) and ctrl.get("id"):
                out.append((str(ctrl["id"]), "catalog.controls"))
        for g in root.get("groups", []) or []:
            walk_group(g, "catalog.groups")

    elif t == "profile":
        for imp in root.get("imports", []) or []:
            for inc in (imp.get("include-controls") or []):
                for wid in (inc.get("with-ids") or []):
                    out.append((str(wid), "profile.imports"))

    elif t == "component-definition":
        for comp in root.get("components", []) or []:
            for cimpl in comp.get("control-implementations", []) or []:
                for req in cimpl.get("implemented-requirements", []) or []:
                    cid = req.get("control-id")
                    if cid:
                        out.append((str(cid),
                                    f"component:{comp.get('title','?')}"))

    elif t == "system-security-plan":
        ci = root.get("control-implementation", {})
        for req in ci.get("implemented-requirements", []) or []:
            cid = req.get("control-id")
            if cid:
                out.append((str(cid), "ssp.control-implementation"))

    return out


# --------------------------------------------------------------------------- #
# controls / coverage
# --------------------------------------------------------------------------- #

def control_ids(doc: Dict[str, Any]) -> List[str]:
    """Flatten a document to its sorted, de-duplicated control-id set."""
    t, root = _root(doc)
    ids = {cid for cid, _loc in _collect_control_ids(t, root)}
    return sorted(ids, key=_control_sort_key)


def _control_sort_key(cid: str):
    m = re.match(r"^([a-z]+)-(\d+)(?:\.(\d+))?$", cid)
    if not m:
        return (cid, 0, 0)
    return (m.group(1), int(m.group(2)), int(m.group(3) or 0))


def coverage(claimed_doc: Dict[str, Any],
             baseline_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Diff the controls a component/SSP claims against a baseline.

    Returns covered / missing / extra control-id sets and a coverage ratio.
    """
    claimed = set(control_ids(claimed_doc))
    baseline = set(control_ids(baseline_doc))
    covered = sorted(claimed & baseline, key=_control_sort_key)
    missing = sorted(baseline - claimed, key=_control_sort_key)
    extra = sorted(claimed - baseline, key=_control_sort_key)
    ratio = (len(covered) / len(baseline)) if baseline else 0.0
    return {
        "baseline_count": len(baseline),
        "claimed_count": len(claimed),
        "covered": covered,
        "missing": missing,
        "extra": extra,
        "coverage_ratio": round(ratio, 4),
    }


def gap_report_md(coverage_result: Dict[str, Any],
                  title: str = "Control Coverage Report") -> str:
    """Render a coverage result as a Markdown gap report (for PRs / audits)."""
    pct = coverage_result["coverage_ratio"] * 100
    lines = [f"# {title}", "",
             f"**Coverage: {pct:.1f}%** "
             f"({len(coverage_result['covered'])}/"
             f"{coverage_result['baseline_count']} baseline controls)", ""]
    lines.append("## Missing controls")
    if coverage_result["missing"]:
        lines.append("")
        lines.append("| Control | Status |")
        lines.append("|---------|--------|")
        for cid in coverage_result["missing"]:
            lines.append(f"| `{cid}` | not implemented |")
    else:
        lines.append("\nNone — every baseline control is covered.")
    if coverage_result["extra"]:
        lines.append("")
        lines.append("## Extra controls (claimed, not in baseline)")
        lines.append("")
        for cid in coverage_result["extra"]:
            lines.append(f"- `{cid}`")
    lines.append("")
    return "\n".join(lines)


def to_sarif(result: "ValidationResult") -> Dict[str, Any]:
    """Render a ValidationResult as a SARIF 2.1.0 log.

    SARIF (Static Analysis Results Interchange Format, OASIS standard) is what
    GitHub code scanning, Azure DevOps, and most CI dashboards ingest. Emitting
    oscalkit's structural findings as SARIF lets OSCAL linting show up next to
    SAST/dependency findings in the same security tab — defensive, authorized
    compliance gating in CI.

    Severities map to SARIF levels: error->error, warning->warning, info->note.
    """
    sarif_level = {"error": "error", "warning": "warning", "info": "note"}

    # Build the rules catalog (one rule per distinct finding `rule`).
    rule_index: Dict[str, int] = {}
    rules: List[Dict[str, Any]] = []
    for f in result.findings:
        if f.rule not in rule_index:
            rule_index[f.rule] = len(rules)
            rules.append({
                "id": f.rule,
                "name": f.rule.replace(".", "_"),
                "shortDescription": {"text": f.rule},
                "defaultConfiguration": {
                    "level": sarif_level.get(f.severity, "warning")},
            })

    results: List[Dict[str, Any]] = []
    for f in result.findings:
        results.append({
            "ruleId": f.rule,
            "ruleIndex": rule_index[f.rule],
            "level": sarif_level.get(f.severity, "warning"),
            "message": {"text": f.message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": result.source},
                },
                "logicalLocations": [{"fullyQualifiedName": f.location}],
            }] if f.location else [{
                "physicalLocation": {
                    "artifactLocation": {"uri": result.source}}}],
        })

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
                   "master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": TOOL_NAME,
                    "version": TOOL_VERSION,
                    "informationUri": "https://github.com/cognis-digital/oscalkit",
                    "rules": rules,
                }
            },
            "properties": {"docType": result.doc_type},
            "results": results,
        }],
    }


def stats(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Summary statistics for an OSCAL document (counts by family + totals)."""
    ids = control_ids(doc)
    families: Dict[str, int] = {}
    for cid in ids:
        fam = cid.split("-")[0]
        families[fam] = families.get(fam, 0) + 1
    return {
        "doc_type": doc_type(doc),
        "control_count": len(ids),
        "family_count": len(families),
        "by_family": dict(sorted(families.items())),
    }


def merge_baselines(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge the control-id sets of several baselines/catalogs into a profile.

    Produces a profile-shaped document selecting the union of all control ids.
    """
    all_ids: set = set()
    for d in docs:
        all_ids.update(control_ids(d))
    selected = sorted(all_ids, key=_control_sort_key)
    return {
        "profile": {
            "uuid": "00000000-0000-4000-8000-000000000000",
            "metadata": {"title": "Merged Baseline",
                         "version": "1.0.0", "oscal-version": "1.1.2"},
            "imports": [{"href": "merged", "include-controls": [
                {"with-ids": selected}]}],
        }
    }


# --------------------------------------------------------------------------- #
# convert
# --------------------------------------------------------------------------- #

def convert(doc: Dict[str, Any], to_format: str) -> str:
    if to_format == "json":
        return json.dumps(doc, indent=2)
    if to_format in ("yaml", "yml"):
        return to_yaml(doc)
    raise OscalError(f"unsupported target format: {to_format}")


# --------------------------------------------------------------------------- #
# AI hook (opt-in, default OFF)
# --------------------------------------------------------------------------- #

def explain_gaps(coverage_result: Dict[str, Any]) -> Dict[str, Any]:
    """Draft remediation notes for missing controls via the local fleet.

    Off by default; returns a deterministic stub unless COGNIS_AI_* is set.
    """
    out = {"missing": coverage_result.get("missing", []),
           "notes": "", "_ai": "disabled — set COGNIS_AI_BACKEND to enable"}
    backend = _load_ai_backend()
    if backend is None or not backend.is_enabled() or not backend.health():
        return out
    prompt = ("For each missing security control id, give a one-line "
              "remediation hint. Return plain text, one line per control.\n\n"
              "MISSING: " + ", ".join(coverage_result.get("missing", [])))
    try:
        out["notes"] = backend._chat("Be concise and concrete.", prompt) or ""
        out["_ai"] = "drafted by local fleet"
    except Exception:
        pass
    return out


def _load_ai_backend():
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.abspath(os.path.join(here, "..", "..", "..", "_shared",
                                        "cognis_ai_backend.py"))
    if os.path.isfile(cand):
        try:
            spec = importlib.util.spec_from_file_location("cognis_ai_backend", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod.CognisAIBackend()
        except Exception:
            return None
    return None
