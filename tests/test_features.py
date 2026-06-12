"""Feature tests for oscalkit — stats, gap-report md, merge, CLI."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oscalkit import (
    control_ids, coverage, gap_report_md, load, merge_baselines, stats,
)
from oscalkit.cli import main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(REPO_ROOT, "demos", "01-basic")
CATALOG = os.path.join(DEMO, "catalog.json")
PROFILE = os.path.join(DEMO, "profile.yaml")
COMPONENT = os.path.join(DEMO, "component-definition.json")


class TestStats(unittest.TestCase):
    def test_catalog_stats(self):
        s = stats(load(CATALOG))
        self.assertEqual(s["doc_type"], "catalog")
        self.assertEqual(s["control_count"], 5)
        # families: ac (3), si (1), ra (1)
        self.assertEqual(s["by_family"]["ac"], 3)
        self.assertEqual(s["family_count"], 3)


class TestGapReport(unittest.TestCase):
    def test_markdown_lists_missing(self):
        cov = coverage(load(COMPONENT), load(PROFILE))
        md = gap_report_md(cov, title="Demo Gaps")
        self.assertIn("# Demo Gaps", md)
        self.assertIn("`ra-5`", md)         # the missing control
        self.assertIn("Coverage: 75.0%", md)

    def test_full_coverage_md(self):
        cov = coverage(load(PROFILE), load(PROFILE))
        md = gap_report_md(cov)
        self.assertIn("every baseline control is covered", md)


class TestMerge(unittest.TestCase):
    def test_merge_union(self):
        merged = merge_baselines([load(CATALOG), load(PROFILE)])
        ids = set(control_ids(merged))
        # union of catalog (5) and profile (4) ids
        self.assertEqual(ids, set(control_ids(load(CATALOG))) |
                         set(control_ids(load(PROFILE))))

    def test_merged_is_valid_profile(self):
        from oscalkit import validate
        merged = merge_baselines([load(CATALOG)])
        self.assertEqual(validate(merged).doc_type, "profile")
        self.assertTrue(validate(merged).ok)


class TestCliFeatures(unittest.TestCase):
    def test_stats_cli(self):
        self.assertEqual(main(["stats", CATALOG]), 0)

    def test_coverage_md_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "gap.md")
            self.assertEqual(main(["coverage", COMPONENT, PROFILE,
                                   "--format", "md", "--out", out]), 0)
            with open(out) as fh:
                self.assertIn("Coverage:", fh.read())

    def test_merge_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "merged.json")
            self.assertEqual(main(["merge", CATALOG, PROFILE, "--out", out]), 0)
            with open(out) as fh:
                data = json.load(fh)
            self.assertEqual(data.get("profile", {}).get("metadata", {}).get("title"),
                             "Merged Baseline")

    def test_merge_to_yaml(self):
        self.assertEqual(main(["merge", CATALOG, "--to", "yaml"]), 0)


if __name__ == "__main__":
    unittest.main()
