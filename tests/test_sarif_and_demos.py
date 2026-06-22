"""Tests for the SARIF 2.1.0 export feature and the bundled demo scenarios.

Standard library only; no network. Every demo listed here is exercised through
the real CLI so the README's claims stay honest.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oscalkit import coverage, load, to_sarif, validate
from oscalkit.cli import main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(REPO_ROOT, "demos")


def d(*parts):
    return os.path.join(DEMOS, *parts)


class TestSarif(unittest.TestCase):
    def test_sarif_shape_on_broken_catalog(self):
        path = d("04-sarif-code-scanning", "broken-catalog.json")
        log = to_sarif(validate(load(path), source=path))
        self.assertEqual(log["version"], "2.1.0")
        self.assertEqual(len(log["runs"]), 1)
        run = log["runs"][0]
        self.assertEqual(run["tool"]["driver"]["name"], "oscalkit")
        # Four deliberate findings in the demo doc.
        self.assertEqual(len(run["results"]), 4)
        levels = {r["level"] for r in run["results"]}
        self.assertEqual(levels, {"error", "warning", "note"})
        # Every result must reference a rule that exists in the driver catalog.
        rule_ids = {ru["id"] for ru in run["tool"]["driver"]["rules"]}
        for r in run["results"]:
            self.assertIn(r["ruleId"], rule_ids)
            self.assertEqual(r["ruleIndex"],
                             next(i for i, ru in
                                  enumerate(run["tool"]["driver"]["rules"])
                                  if ru["id"] == r["ruleId"]))

    def test_sarif_clean_doc_has_no_results(self):
        path = d("08-full-coverage-pass", "edge-agent.json")
        log = to_sarif(validate(load(path), source=path))
        self.assertEqual(log["runs"][0]["results"], [])
        self.assertEqual(log["version"], "2.1.0")

    def test_sarif_is_valid_json_via_cli(self):
        path = d("04-sarif-code-scanning", "broken-catalog.json")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.sarif")
            # validate exits 1 because the doc has an error-severity finding.
            self.assertEqual(main(["validate", path, "--format", "sarif",
                                   "--out", out]), 1)
            with open(out, encoding="utf-8") as fh:
                doc = json.load(fh)
            self.assertEqual(doc["version"], "2.1.0")


class TestDemoCoverage(unittest.TestCase):
    def test_demo02_low_gap(self):
        cov = coverage(load(d("02-nist80053-low-gap", "saas-component.json")),
                       load(d("02-nist80053-low-gap", "low-baseline.json")))
        self.assertEqual(cov["baseline_count"], 13)
        self.assertEqual(cov["missing"], ["ac-8", "au-6", "ra-5"])

    def test_demo03_gate_fails_then_passes(self):
        ssp = d("03-ci-coverage-gate", "ssp.json")
        base = d("03-ci-coverage-gate", "moderate-baseline.yaml")
        self.assertEqual(main(["coverage", ssp, base,
                               "--min-coverage", "0.95"]), 1)
        self.assertEqual(main(["coverage", ssp, base,
                               "--min-coverage", "0.75"]), 0)

    def test_demo05_roundtrip_preserves_controls(self):
        from oscalkit import control_ids, convert, parse_yaml_subset
        orig = load(d("05-json-yaml-roundtrip", "component.json"))
        back = parse_yaml_subset(convert(orig, "yaml"))
        self.assertEqual(control_ids(orig), control_ids(back))
        self.assertEqual(control_ids(orig), ["au-2", "sc-8", "sc-13"])

    def test_demo06_merge_union_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "merged.json")
            self.assertEqual(main(["merge",
                                   d("06-merge-baselines", "low.json"),
                                   d("06-merge-baselines", "moderate.yaml"),
                                   "--out", out]), 0)
            from oscalkit import control_ids
            ids = control_ids(load(out))
            self.assertEqual(len(ids), 11)
            self.assertTrue(validate(load(out)).ok)

    def test_demo07_stats(self):
        from oscalkit import stats
        s = stats(load(d("07-portfolio-stats", "portfolio-catalog.json")))
        self.assertEqual(s["control_count"], 13)
        self.assertEqual(s["by_family"]["ac"], 5)
        self.assertEqual(s["family_count"], 4)

    def test_demo08_full_coverage(self):
        cov = coverage(load(d("08-full-coverage-pass", "edge-agent.json")),
                       load(d("08-full-coverage-pass", "baseline.yaml")))
        self.assertEqual(cov["coverage_ratio"], 1.0)
        self.assertEqual(cov["missing"], [])


class TestDemoDocsValidate(unittest.TestCase):
    """Every demo input that should be structurally clean must validate."""

    CLEAN = [
        ("02-nist80053-low-gap", "catalog.json"),
        ("02-nist80053-low-gap", "low-baseline.json"),
        ("02-nist80053-low-gap", "saas-component.json"),
        ("03-ci-coverage-gate", "ssp.json"),
        ("03-ci-coverage-gate", "moderate-baseline.yaml"),
        ("05-json-yaml-roundtrip", "component.json"),
        ("06-merge-baselines", "low.json"),
        ("06-merge-baselines", "moderate.yaml"),
        ("07-portfolio-stats", "portfolio-catalog.json"),
        ("08-full-coverage-pass", "baseline.yaml"),
        ("08-full-coverage-pass", "edge-agent.json"),
    ]

    def test_clean_demos_pass_validation(self):
        for parts in self.CLEAN:
            path = d(*parts)
            res = validate(load(path), source=path)
            self.assertTrue(res.ok, f"{path}: {res.to_dict()}")

    def test_every_demo_dir_has_scenario(self):
        for name in os.listdir(DEMOS):
            sub = os.path.join(DEMOS, name)
            if os.path.isdir(sub):
                self.assertTrue(
                    os.path.isfile(os.path.join(sub, "SCENARIO.md")),
                    f"{name} missing SCENARIO.md")


if __name__ == "__main__":
    unittest.main()
