"""Deep tests for oscalkit — YAML round-trip, controls, coverage, validate, MCP."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oscalkit import (
    control_ids,
    convert,
    coverage,
    explain_gaps,
    load,
    parse_yaml_subset,
    to_yaml,
    validate,
)
from oscalkit.core import doc_type, OscalError
from oscalkit import mcp_server

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(REPO_ROOT, "demos", "01-basic")
CATALOG = os.path.join(DEMO, "catalog.json")
PROFILE = os.path.join(DEMO, "profile.yaml")
COMPONENT = os.path.join(DEMO, "component-definition.json")


class TestYamlRoundTrip(unittest.TestCase):
    def test_json_to_yaml_and_back(self):
        doc = load(CATALOG)
        ytext = convert(doc, "yaml")
        back = parse_yaml_subset(ytext)
        # Control id sets must survive the round-trip.
        self.assertEqual(control_ids({"catalog": back["catalog"]}),
                         control_ids(doc))

    def test_to_yaml_parse_identity_on_nested(self):
        data = {"a": {"b": [1, 2], "c": "x: y"}, "list": [{"id": "ac-1"}]}
        self.assertEqual(parse_yaml_subset(to_yaml(data)), data)


class TestControls(unittest.TestCase):
    def test_catalog_controls(self):
        ids = control_ids(load(CATALOG))
        self.assertEqual(ids, ["ac-1", "ac-2", "ac-2.1", "ra-5", "si-4"])

    def test_profile_controls(self):
        ids = control_ids(load(PROFILE))
        self.assertEqual(set(ids), {"ac-1", "ac-2", "si-4", "ra-5"})

    def test_component_controls(self):
        ids = control_ids(load(COMPONENT))
        self.assertEqual(set(ids), {"ac-1", "ac-2", "si-4"})


class TestCoverage(unittest.TestCase):
    def test_component_vs_profile(self):
        cov = coverage(load(COMPONENT), load(PROFILE))
        self.assertEqual(cov["baseline_count"], 4)
        self.assertEqual(set(cov["covered"]), {"ac-1", "ac-2", "si-4"})
        self.assertEqual(cov["missing"], ["ra-5"])
        self.assertEqual(cov["extra"], [])
        self.assertAlmostEqual(cov["coverage_ratio"], 0.75)

    def test_full_coverage(self):
        cov = coverage(load(PROFILE), load(PROFILE))
        self.assertEqual(cov["coverage_ratio"], 1.0)
        self.assertEqual(cov["missing"], [])


class TestValidateFailures(unittest.TestCase):
    def test_unknown_root(self):
        res = validate({"foo": {}})
        self.assertFalse(res.ok)
        self.assertEqual(res.doc_type, "unknown")

    def test_missing_metadata_and_uuid(self):
        res = validate({"catalog": {"groups": [{"controls": [{"id": "ac-1"}]}]}})
        rules = {f.rule for f in res.findings}
        self.assertIn("metadata.missing", rules)
        self.assertIn("uuid.missing", rules)

    def test_empty_catalog(self):
        res = validate({"catalog": {"uuid": "x", "metadata": {"title": "t", "version": "1"}}})
        rules = {f.rule for f in res.findings}
        self.assertIn("catalog.empty", rules)

    def test_profile_requires_imports(self):
        res = validate({"profile": {"uuid": "x", "metadata": {"title": "t", "version": "1"}}})
        rules = {f.rule for f in res.findings}
        self.assertIn("profile.no_imports", rules)

    def test_doc_type_detection(self):
        self.assertEqual(doc_type(load(COMPONENT)), "component-definition")


class TestConvert(unittest.TestCase):
    def test_bad_target_raises(self):
        with self.assertRaises(OscalError):
            convert({"catalog": {}}, "xml")

    def test_convert_writes_yaml(self):
        text = convert(load(CATALOG), "yaml")
        self.assertIn("ac-1", text)


class TestMcp(unittest.TestCase):
    def test_list_and_coverage(self):
        tl = mcp_server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {t["name"] for t in tl["result"]["tools"]}
        self.assertEqual(names, {"validate", "controls", "coverage"})
        r = mcp_server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "coverage",
                       "arguments": {"claimed": COMPONENT, "baseline": PROFILE}}})
        payload = json.loads(r["result"]["content"][0]["text"])
        self.assertEqual(payload["missing"], ["ra-5"])

    def test_validate_isError_on_bad_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w") as fh:
                json.dump({"foo": {}}, fh)
            r = mcp_server.handle_request({
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "validate", "arguments": {"file": bad}}})
            self.assertTrue(r["result"]["isError"])


class TestAiHook(unittest.TestCase):
    def test_off_by_default(self):
        for v in ("COGNIS_AI_BACKEND", "COGNIS_AI_ENDPOINT"):
            os.environ.pop(v, None)
        out = explain_gaps({"missing": ["ra-5"]})
        self.assertTrue(out["_ai"].startswith("disabled"))


if __name__ == "__main__":
    unittest.main()
