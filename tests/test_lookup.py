from pathlib import Path
import importlib.util
import os
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/asd-ste100/scripts/lookup_standard.py"
spec = importlib.util.spec_from_file_location("lookup_standard", SCRIPT)
lookup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lookup)


class LocalLookupTests(unittest.TestCase):
    def test_query_is_literal_not_regular_expression(self):
        self.assertEqual(len(lookup.matches("Use A+B here and AAB there.", "A+B")), 1)

    def test_query_handles_pdf_line_breaks(self):
        self.assertEqual(len(lookup.matches("Rule\n  5.1 is here.", "Rule 5.1")), 1)

    def test_empty_query_is_rejected(self):
        with self.assertRaises(ValueError):
            lookup.matches("text", "  ")

    def test_explicit_source_environment_takes_priority(self):
        with patch.dict(os.environ, {"ASD_STE100_PDF": "/private/selected.pdf"}):
            self.assertEqual(lookup.default_pdf_path(), "/private/selected.pdf")

    def test_private_standard_discovery_uses_configured_codex_home(self):
        with tempfile.TemporaryDirectory() as temp:
            standard = Path(temp) / "standards/asd-ste100/ASD-STE100_ISSUE9.pdf"
            standard.parent.mkdir(parents=True)
            standard.write_bytes(b"local fixture")
            with patch.dict(os.environ, {"CODEX_HOME": temp}):
                os.environ.pop("ASD_STE100_PDF", None)
                self.assertEqual(Path(lookup.default_pdf_path()), standard)


if __name__ == "__main__":
    unittest.main()
