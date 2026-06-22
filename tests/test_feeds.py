"""Offline tests for the oscalkit data-feed integration.

Zero network: COGNIS_FEEDS_CACHE is pointed at a trimmed NIST 800-53 rev5
fixture under tests/fixtures/feeds-cache and every read uses offline=True.
"""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_CACHE = os.path.join(REPO_ROOT, "tests", "fixtures", "feeds-cache")
DEMO = os.path.join(REPO_ROOT, "demos", "01-basic")

# Point the bundled ingestion engine at the offline fixture cache before import.
os.environ["COGNIS_FEEDS_CACHE"] = FIXTURE_CACHE

from oscalkit import datafeeds, feeds  # noqa: E402
from oscalkit.cli import main  # noqa: E402


class TestFixturePresent(unittest.TestCase):
    def test_cache_files_exist(self):
        self.assertTrue(os.path.isdir(FIXTURE_CACHE))
        self.assertTrue(os.path.exists(
            os.path.join(FIXTURE_CACHE, "oscal-800-53-rev5-catalog.data")))


class TestCatalogScope(unittest.TestCase):
    def test_relevant_feeds_only(self):
        ids = [f["id"] for f in feeds.relevant_feeds()]
        self.assertEqual(ids, ["oscal-800-53-rev5-catalog"])

    def test_irrelevant_feed_rejected(self):
        with self.assertRaises(KeyError):
            feeds.get("cisa-kev", offline=True)
        with self.assertRaises(KeyError):
            feeds.update("epss")

    def test_catalog_loads_full_17_feeds(self):
        # the bundled catalog still ships all feeds; oscalkit just filters them
        cat = datafeeds.load_catalog()
        self.assertEqual(len(cat["feeds"]), 17)


class TestOfflineGet(unittest.TestCase):
    def test_get_offline_serves_cache(self):
        doc = feeds.get(offline=True)
        self.assertIn("catalog", doc)
        self.assertTrue(doc["catalog"]["groups"])

    def test_offline_missing_raises(self):
        # an unknown-but-relevant cache miss is impossible (only one feed), so
        # verify datafeeds raises for an uncached feed when offline.
        with self.assertRaises(FileNotFoundError):
            datafeeds.get("epss", offline=True)


class TestTitleResolution(unittest.TestCase):
    def test_title_index(self):
        idx = feeds.title_index(offline=True)
        self.assertEqual(idx["ac-1"]["title"], "Policy and Procedures")
        self.assertEqual(idx["ac-1"]["family"], "Access Control")

    def test_enhancement_titles(self):
        idx = feeds.title_index(offline=True)
        # nested enhancement ids resolve too
        self.assertIn("ac-2.1", idx)
        self.assertEqual(idx["ac-2.1"]["title"],
                         "Automated System Account Management")

    def test_resolve_titles_unknown_blank(self):
        res = feeds.resolve_titles(["ac-1", "zz-99"], offline=True)
        self.assertEqual(res["ac-1"], "Policy and Procedures")
        self.assertEqual(res["zz-99"], "")

    def test_family_name(self):
        self.assertEqual(feeds.family_name("ac"), "Access Control")


class TestCliFeeds(unittest.TestCase):
    def _run(self, args):
        from io import StringIO
        buf = StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = main(args)
        finally:
            sys.stdout = old
        return rc, buf.getvalue()

    def test_feeds_list(self):
        rc, out = self._run(["feeds", "list"])
        self.assertEqual(rc, 0)
        self.assertIn("oscal-800-53-rev5-catalog", out)
        # irrelevant feeds must not leak into the listing
        self.assertNotIn("cisa-kev", out)

    def test_feeds_list_json(self):
        rc, out = self._run(["feeds", "list", "--format", "json"])
        self.assertEqual(rc, 0)
        rows = json.loads(out)
        self.assertEqual([r["id"] for r in rows], ["oscal-800-53-rev5-catalog"])

    def test_feeds_get_offline(self):
        rc, out = self._run(["feeds", "get", "--offline"])
        self.assertEqual(rc, 0)
        self.assertIn("catalog", out)

    def test_feeds_get_irrelevant_fails(self):
        rc, out = self._run(["feeds", "get", "cisa-kev", "--offline"])
        self.assertEqual(rc, 1)


class TestCliEnrichment(unittest.TestCase):
    def _run(self, args):
        from io import StringIO
        buf = StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = main(args)
        finally:
            sys.stdout = old
        return rc, buf.getvalue()

    def test_controls_enrich_offline(self):
        catalog = os.path.join(DEMO, "catalog.json")
        rc, out = self._run(["controls", catalog, "--enrich", "--offline"])
        self.assertEqual(rc, 0)
        # demo catalog includes ac-1; its real NIST title should appear
        self.assertIn("Policy and Procedures", out)

    def test_controls_enrich_json(self):
        catalog = os.path.join(DEMO, "catalog.json")
        rc, out = self._run(
            ["controls", catalog, "--enrich", "--offline", "--format", "json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["source"], "nist-800-53-rev5")
        titled = {c["id"]: c["title"] for c in payload["controls"]}
        self.assertEqual(titled.get("ac-1"), "Policy and Procedures")


class TestSnapshotRoundtrip(unittest.TestCase):
    def test_snapshot_export_import(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            snap = os.path.join(td, "feeds.tar.gz")
            n = datafeeds.snapshot_export(snap)
            self.assertGreaterEqual(n, 1)
            self.assertTrue(os.path.exists(snap))
            # importing back into the same cache is idempotent
            n2 = datafeeds.snapshot_import(snap)
            self.assertGreaterEqual(n2, 1)


if __name__ == "__main__":
    unittest.main()
