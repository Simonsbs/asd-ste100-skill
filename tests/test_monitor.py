from __future__ import annotations

from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from email.message import Message

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_sources import accept_report, build_report, canonical_url, fetch_source, fingerprint, load_catalog


URL = "https://www.asd-ste100.org/STE_faq.html"


def source(source_id="faq", url=URL, **changes):
    return {"id": source_id, "url": url, "kind": "html", "monitor": True, **changes}


def success(digest="a" * 64, **changes):
    return {"ok": True, "sha256": digest, "final_url": URL, "status": 200, "bytes": 42, "kind": "html", "content_type": "text/html", "links": [], **changes}


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, content_type="text/html"):
        super().__init__(data)
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def geturl(self):
        return URL


class FingerprintTests(unittest.TestCase):
    def test_presentation_and_script_edits_do_not_change_content_hash(self):
        first = b'<html><style>.a { color:red }</style><body><nav>Menu 1</nav><p>Issue 9 is current.</p><script>var a=1</script></body></html>'
        second = b'<html><style>.b { color:blue }</style><body><nav>Menu 2</nav><p class="new">Issue 9\n is current.</p><script>var a=2</script></body></html>'
        self.assertEqual(fingerprint(first, "html", URL)[0], fingerprint(second, "html", URL)[0])

    def test_edition_and_link_changes_are_visible(self):
        before = b'<p>Issue 9</p><a href="old.pdf">Standard</a>'
        after = b'<p>Issue 10</p><a href="new.pdf">Standard</a>'
        self.assertNotEqual(fingerprint(before, "html", URL)[0], fingerprint(after, "html", URL)[0])
        self.assertIn("https://www.asd-ste100.org/new.pdf", fingerprint(after, "html", URL)[1])

    def test_zenodo_counters_do_not_trigger_changes(self):
        before = {"id": 1, "doi": "test", "metadata": {"title": "Issue 9"}, "stats": {"downloads": 10}}
        after = deepcopy(before)
        after["stats"]["downloads"] = 99
        after["updated"] = "a later API timestamp"
        self.assertEqual(fingerprint(json.dumps(before).encode(), "json", URL)[0], fingerprint(json.dumps(after).encode(), "json", URL)[0])

    def test_zenodo_license_and_checksum_changes_are_visible(self):
        before = {"metadata": {"license": {"id": "old"}}, "files": [{"key": "standard.pdf", "checksum": "a"}]}
        after = deepcopy(before)
        after["files"][0]["checksum"] = "b"
        self.assertNotEqual(fingerprint(json.dumps(before).encode(), "json", URL)[0], fingerprint(json.dumps(after).encode(), "json", URL)[0])
        after = deepcopy(before)
        after["metadata"]["license"]["id"] = "new"
        self.assertNotEqual(fingerprint(json.dumps(before).encode(), "json", URL)[0], fingerprint(json.dumps(after).encode(), "json", URL)[0])

    def test_sitemap_detects_new_pages_but_ignores_layout(self):
        first = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://asd-ste100.org/index.html</loc></url></urlset>'
        second = first.replace(b"><", b">\n<")
        self.assertEqual(fingerprint(first, "sitemap", URL)[0], fingerprint(second, "sitemap", URL)[0])
        self.assertEqual(fingerprint(first, "sitemap", URL)[1], ["https://www.asd-ste100.org/"])

    def test_binary_hash_is_content_sensitive(self):
        self.assertNotEqual(fingerprint(b"one", "binary", URL)[0], fingerprint(b"two", "binary", URL)[0])


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {"sources": [source()]}
        self.baseline = {"sources": {"faq": success()}}

    def test_unchanged_sources_are_not_changes(self):
        report = build_report(self.catalog, self.baseline, {"faq": success()})
        self.assertFalse(report["has_changes"])
        self.assertEqual(report["errors"], [])

    def test_content_change_is_reported(self):
        report = build_report(self.catalog, self.baseline, {"faq": success("b" * 64)})
        self.assertTrue(report["has_changes"])
        self.assertEqual(report["changes"][0]["id"], "faq")

    def test_failed_retrieval_does_not_erase_the_reviewed_baseline(self):
        report = build_report(self.catalog, self.baseline, {"faq": {"ok": False, "error": "HTTP 403"}})
        self.assertFalse(report["has_changes"])
        self.assertEqual(len(report["errors"]), 1)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "baseline.json"
            target.write_text("keep this baseline", encoding="utf-8")
            with self.assertRaises(ValueError):
                accept_report(report, target)
            self.assertEqual(target.read_text(), "keep this baseline")

    def test_discovered_official_document_requires_classification(self):
        result = success(links=["https://www.asd-ste100.org/assets/files/ISSUE10.pdf"])
        report = build_report(self.catalog, self.baseline, {"faq": result})
        self.assertTrue(report["has_changes"])
        self.assertEqual(len(report["discovered_urls"]), 1)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                accept_report(report, Path(temp) / "baseline.json")

    def test_known_url_alias_is_not_new_source(self):
        self.catalog["sources"].append(source("home", "https://asd-ste100.org/index.html", monitor=False))
        report = build_report(self.catalog, self.baseline, {"faq": success(links=["https://www.asd-ste100.org/"])})
        self.assertEqual(report["discovered_urls"], [])

    def test_removed_monitor_entry_is_visible(self):
        report = build_report({"sources": []}, self.baseline, {})
        self.assertEqual(report["changes"][0]["change"], "removed-from-monitoring")

    def test_new_source_is_visible(self):
        report = build_report(self.catalog, {"sources": {}}, {"faq": success()})
        self.assertEqual(report["changes"][0]["change"], "new-source")

    def test_accepted_baseline_contains_no_publication_text_or_links(self):
        report = build_report(self.catalog, self.baseline, {"faq": success(links=[URL])})
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "baseline.json"
            accept_report(report, target)
            saved = json.loads(target.read_text())
            self.assertNotIn("links", saved["sources"]["faq"])
            self.assertNotIn("ok", saved["sources"]["faq"])
            self.assertEqual(saved["sources"]["faq"]["sha256"], "a" * 64)

    def test_duplicate_source_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "catalog.json"
            target.write_text(json.dumps({"schema_version": 1, "sources": [source(), source()]}))
            with self.assertRaises(ValueError):
                load_catalog(target)

    def test_credentials_in_url_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "catalog.json"
            target.write_text(json.dumps({"schema_version": 1, "sources": [source(url="https://user:password@example.com/file")]}))
            with self.assertRaises(ValueError):
                load_catalog(target)

    def test_pdf_download_that_returns_html_is_not_accepted(self):
        pdf_source = source(url="https://www.asd-ste100.org/standard.pdf", kind="binary")
        with patch("check_sources.urlopen", side_effect=lambda *args, **kwargs: Response(b"<html>Challenge</html>")):
            result = fetch_source(pdf_source)
        self.assertFalse(result["ok"])

    def test_size_limit_is_enforced(self):
        with patch("check_sources.MAX_BYTES", 8), patch("check_sources.urlopen", side_effect=lambda *args, **kwargs: Response(b"x" * 20)):
            result = fetch_source(source())
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
