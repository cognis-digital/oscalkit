"""Smoke tests for oscalkit. Standard library only, no network."""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oscalkit import TOOL_NAME, TOOL_VERSION, load, validate
from oscalkit.cli import main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(REPO_ROOT, "demos", "01-basic")
CATALOG = os.path.join(DEMO, "catalog.json")
PROFILE = os.path.join(DEMO, "profile.yaml")
COMPONENT = os.path.join(DEMO, "component-definition.json")


class TestMetadata(unittest.TestCase):
    def test_metadata(self):
        self.assertEqual(TOOL_NAME, "oscalkit")
        self.assertTrue(TOOL_VERSION)


class TestValidate(unittest.TestCase):
    def test_catalog_valid(self):
        res = validate(load(CATALOG), CATALOG)
        self.assertTrue(res.ok, res.to_dict())
        self.assertEqual(res.doc_type, "catalog")

    def test_profile_valid(self):
        res = validate(load(PROFILE), PROFILE)
        self.assertTrue(res.ok, res.to_dict())
        self.assertEqual(res.doc_type, "profile")

    def test_component_valid(self):
        res = validate(load(COMPONENT), COMPONENT)
        self.assertTrue(res.ok, res.to_dict())


class TestCli(unittest.TestCase):
    def test_validate_passes(self):
        self.assertEqual(main(["validate", CATALOG]), 0)

    def test_coverage_json(self):
        proc = subprocess.run(
            [sys.executable, "-m", "oscalkit", "coverage", COMPONENT, PROFILE,
             "--format", "json"],
            cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIn("ra-5", data["missing"])

    def test_controls_listing(self):
        self.assertEqual(main(["controls", CATALOG]), 0)

    def test_missing_file_exits_2(self):
        self.assertEqual(main(["validate", "/no/such/file.json"]), 2)

    def test_no_command_exits_2(self):
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
