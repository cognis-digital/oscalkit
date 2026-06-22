"""Command-line interface for oscalkit."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from oscalkit import TOOL_NAME, TOOL_VERSION
from oscalkit.core import (
    OscalError,
    control_ids,
    convert,
    coverage,
    load,
    validate,
)

_SEV = {"error": "ERR ", "warning": "WARN", "info": "INFO"}


def _emit(text: str, out: Optional[str]) -> None:
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="OSCAL compliance-as-code — validate, convert, and diff "
                    "control coverage for catalogs, profiles, component "
                    "definitions, and SSPs.")
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = p.add_subparsers(dest="command")

    v = sub.add_parser("validate", help="Structural + referential checks.")
    v.add_argument("file", help="OSCAL JSON/YAML document.")
    v.add_argument("--format", choices=("table", "json", "sarif"),
                   default="table")
    v.add_argument("--out", help="Write report to a file.")
    v.add_argument("--fail-on", choices=("error", "warning", "info"),
                   default="error", help="Exit non-zero at/above this severity.")

    c = sub.add_parser("convert", help="Convert OSCAL between JSON and YAML.")
    c.add_argument("file")
    c.add_argument("--to", choices=("json", "yaml"), required=True)
    c.add_argument("--out", help="Write converted document to a file.")

    ctl = sub.add_parser("controls", help="List the control ids a document covers.")
    ctl.add_argument("file")
    ctl.add_argument("--format", choices=("table", "json"), default="table")
    ctl.add_argument("--enrich", action="store_true",
                     help="Resolve official control titles from the NIST "
                          "800-53 rev5 OSCAL feed.")
    ctl.add_argument("--offline", action="store_true",
                     help="Use only the cached feed (no network).")

    cov = sub.add_parser("coverage", help="Diff claimed controls vs a baseline.")
    cov.add_argument("claimed", help="Component-definition or SSP.")
    cov.add_argument("baseline", help="Catalog or profile baseline.")
    cov.add_argument("--format", choices=("table", "json", "md"), default="table")
    cov.add_argument("--out", help="Write report to a file.")
    cov.add_argument("--min-coverage", type=float, default=None,
                     help="Exit non-zero if coverage ratio is below this (0..1).")
    cov.add_argument("--enrich", action="store_true",
                     help="Annotate missing controls with NIST 800-53 rev5 titles.")
    cov.add_argument("--offline", action="store_true",
                     help="Use only the cached feed (no network).")

    st = sub.add_parser("stats", help="Summary stats (controls by family).")
    st.add_argument("file")
    st.add_argument("--format", choices=("table", "json"), default="table")

    mg = sub.add_parser("merge", help="Merge baselines/catalogs into one profile.")
    mg.add_argument("files", nargs="+")
    mg.add_argument("--to", choices=("json", "yaml"), default="json")
    mg.add_argument("--out")

    sub.add_parser("mcp", help="Run as an MCP server (stdio JSON-RPC).")

    # --- data feeds (edge / air-gap) -------------------------------------- #
    fe = sub.add_parser(
        "feeds",
        help="Real NIST 800-53 control-catalog feed (edge/air-gap deployable).")
    fesub = fe.add_subparsers(dest="feeds_cmd")
    fl = fesub.add_parser("list", help="List the feeds oscalkit consumes.")
    fl.add_argument("--format", choices=("table", "json"), default="table")
    fu = fesub.add_parser("update", help="Fetch + cache a feed.")
    fu.add_argument("feed", nargs="?", default="oscal-800-53-rev5-catalog")
    fg = fesub.add_parser("get", help="Print a cached/fetched feed.")
    fg.add_argument("feed", nargs="?", default="oscal-800-53-rev5-catalog")
    fg.add_argument("--offline", action="store_true")
    fx = fesub.add_parser("snapshot-export",
                          help="Tar the feed cache for air-gap transfer.")
    fx.add_argument("path")
    fi = fesub.add_parser("snapshot-import",
                          help="Load a feed-cache snapshot into the local cache.")
    fi.add_argument("path")
    return p


def _run_validate(a) -> int:
    try:
        doc = load(a.file)
    except (OSError, OscalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    res = validate(doc, source=a.file)
    if a.format == "json":
        _emit(json.dumps(res.to_dict(), indent=2), a.out)
    elif a.format == "sarif":
        from oscalkit import to_sarif
        _emit(json.dumps(to_sarif(res), indent=2), a.out)
    else:
        lines = [f"oscalkit validate — {res.source}  ({res.doc_type})", "=" * 64]
        if not res.findings:
            lines.append("No findings. Document passes structural checks.")
        for f in res.findings:
            lines.append(f"[{_SEV.get(f.severity, f.severity)}] {f.rule}: {f.message}")
            if f.location:
                lines.append(f"        at: {f.location}")
        lines.append("-" * 64)
        lines.append("RESULT: " + ("PASS" if res.ok else f"FAIL ({res.errors} error(s))"))
        _emit("\n".join(lines), a.out)
    order = {"error": 0, "warning": 1, "info": 2}
    threshold = order[a.fail_on]
    return 1 if any(order[f.severity] <= threshold for f in res.findings) else 0


def _run_convert(a) -> int:
    try:
        doc = load(a.file)
        text = convert(doc, a.to)
    except (OSError, OscalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _emit(text, a.out)
    return 0


def _run_controls(a) -> int:
    try:
        ids = control_ids(load(a.file))
    except (OSError, OscalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    titles = {}
    if getattr(a, "enrich", False):
        from oscalkit import feeds
        titles = feeds.resolve_titles(ids, offline=getattr(a, "offline", False))
    if a.format == "json":
        if titles:
            payload = {"controls": [{"id": c, "title": titles.get(c, "")} for c in ids],
                       "count": len(ids), "source": "nist-800-53-rev5"}
        else:
            payload = {"controls": ids, "count": len(ids)}
        _emit(json.dumps(payload, indent=2), None)
    else:
        print(f"oscalkit controls — {len(ids)} control(s)")
        if titles:
            for c in ids:
                t = titles.get(c, "")
                print(f"  {c:<10} {t}" if t else f"  {c:<10} (title not in catalog)")
        else:
            print("  " + ", ".join(ids))
    return 0


def _run_coverage(a) -> int:
    try:
        cov = coverage(load(a.claimed), load(a.baseline))
    except (OSError, OscalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    titles = {}
    if getattr(a, "enrich", False):
        from oscalkit import feeds
        titles = feeds.resolve_titles(cov["missing"], offline=getattr(a, "offline", False))
        cov = dict(cov)
        cov["missing_titles"] = titles
    if a.format == "json":
        _emit(json.dumps(cov, indent=2), a.out)
    elif a.format == "md":
        from oscalkit import gap_report_md
        _emit(gap_report_md(cov, titles=titles or None), a.out)
    else:
        pct = cov["coverage_ratio"] * 100
        if titles:
            missing_txt = ", ".join(
                f"{c} ({titles[c]})" if titles.get(c) else c for c in cov["missing"]
            ) if cov["missing"] else "(none)"
        else:
            missing_txt = ", ".join(cov["missing"]) if cov["missing"] else "(none)"
        lines = [f"oscalkit coverage — {pct:.1f}% of baseline", "=" * 64,
                 f"  baseline controls : {cov['baseline_count']}",
                 f"  claimed controls  : {cov['claimed_count']}",
                 f"  covered           : {len(cov['covered'])}",
                 f"  MISSING           : {len(cov['missing'])}  {missing_txt}",
                 f"  extra (not in base): {len(cov['extra'])}  "
                 f"{', '.join(cov['extra']) if cov['extra'] else '(none)'}"]
        _emit("\n".join(lines), a.out)
    if a.min_coverage is not None and cov["coverage_ratio"] < a.min_coverage:
        return 1
    return 0


def _run_feeds(a) -> int:
    from oscalkit import datafeeds, feeds
    if a.feeds_cmd == "list":
        rows = feeds.relevant_feeds()
        if a.format == "json":
            _emit(json.dumps(rows, indent=2), None)
        else:
            print("oscalkit feeds — consumed feeds (compliance domain)")
            for f in rows:
                age = datafeeds.cached_age_hours(f["id"])
                fresh = "uncached" if age is None else f"{age:.1f}h old"
                print(f"  {f['id']:32} [{fresh}]  {f['name']}")
                print(f"    {f['url']}")
        return 0
    if a.feeds_cmd == "update":
        try:
            pth = feeds.update(a.feed)
        except (KeyError, ConnectionError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"updated {a.feed} -> {pth} ({pth.stat().st_size} bytes)")
        return 0
    if a.feeds_cmd == "get":
        try:
            data = feeds.get(a.feed, offline=a.offline)
        except (KeyError, FileNotFoundError, ConnectionError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        out = json.dumps(data, indent=2)[:4000] if isinstance(data, (dict, list)) else str(data)[:4000]
        print(out)
        return 0
    if a.feeds_cmd == "snapshot-export":
        n = datafeeds.snapshot_export(a.path)
        print(f"exported {n} feed(s) -> {a.path}")
        return 0
    if a.feeds_cmd == "snapshot-import":
        n = datafeeds.snapshot_import(a.path)
        print(f"imported {n} feed(s) from {a.path}")
        return 0
    print("usage: oscalkit feeds {list|update|get|snapshot-export|snapshot-import}",
          file=sys.stderr)
    return 2


def _run_stats(a) -> int:
    from oscalkit import stats
    try:
        s = stats(load(a.file))
    except (OSError, OscalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.format == "json":
        _emit(json.dumps(s, indent=2), None)
    else:
        print(f"oscalkit stats — {s['doc_type']}")
        print("=" * 64)
        print(f"  controls : {s['control_count']}   families: {s['family_count']}")
        for fam, n in s["by_family"].items():
            print(f"    {fam:<6} {n}")
    return 0


def _run_merge(a) -> int:
    from oscalkit import convert, merge_baselines
    try:
        merged = merge_baselines([load(f) for f in a.files])
    except (OSError, OscalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _emit(convert(merged, a.to), a.out)
    return 0


def _run_mcp() -> int:
    from oscalkit.mcp_server import run_mcp_server
    run_mcp_server()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        return _run_validate(args)
    if args.command == "convert":
        return _run_convert(args)
    if args.command == "controls":
        return _run_controls(args)
    if args.command == "coverage":
        return _run_coverage(args)
    if args.command == "stats":
        return _run_stats(args)
    if args.command == "merge":
        return _run_merge(args)
    if args.command == "mcp":
        return _run_mcp()
    if args.command == "feeds":
        return _run_feeds(args)
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
