from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sync_install import safe_child, synchronize


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source"
        self.destination = self.root / "codex/skills/asd-ste100"
        self.record = self.root / "codex/skill-state/asd-ste100.json"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text("original skill", encoding="utf-8")
        (self.source / "VERSION").write_text("0.1.0", encoding="utf-8")
        shutil.copytree(self.source, self.destination)

    def adopt(self):
        synchronize(self.source, self.destination, self.record, adopt=True)

    def test_adoption_requires_an_identical_installed_copy(self):
        (self.destination / "SKILL.md").write_text("user change", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.adopt()
        self.assertFalse(self.record.exists())

    def test_update_refuses_modified_installed_file(self):
        self.adopt()
        (self.destination / "SKILL.md").write_text("user change", encoding="utf-8")
        (self.source / "SKILL.md").write_text("upstream change", encoding="utf-8")
        with self.assertRaises(ValueError):
            synchronize(self.source, self.destination, self.record)
        self.assertEqual((self.destination / "SKILL.md").read_text(), "user change")

    def test_update_copies_changes_and_preserves_unrelated_files(self):
        self.adopt()
        (self.destination / "my-notes.txt").write_text("keep", encoding="utf-8")
        (self.source / "SKILL.md").write_text("upstream change", encoding="utf-8")
        synchronize(self.source, self.destination, self.record)
        self.assertEqual((self.destination / "SKILL.md").read_text(), "upstream change")
        self.assertEqual((self.destination / "my-notes.txt").read_text(), "keep")

    def test_upstream_removal_only_removes_managed_file(self):
        self.adopt()
        (self.source / "VERSION").unlink()
        (self.destination / "my-notes.txt").write_text("keep", encoding="utf-8")
        synchronize(self.source, self.destination, self.record)
        self.assertFalse((self.destination / "VERSION").exists())
        self.assertTrue((self.destination / "my-notes.txt").exists())

    def test_check_does_not_modify_files_or_record(self):
        self.adopt()
        old_record = self.record.read_bytes()
        (self.source / "SKILL.md").write_text("upstream change", encoding="utf-8")
        result = synchronize(self.source, self.destination, self.record, check=True)
        self.assertEqual(result, "Managed update available.")
        self.assertEqual(self.record.read_bytes(), old_record)
        self.assertEqual((self.destination / "SKILL.md").read_text(), "original skill")

    def test_new_upstream_file_cannot_overwrite_unmanaged_file(self):
        self.adopt()
        (self.source / "notes.txt").write_text("upstream", encoding="utf-8")
        (self.destination / "notes.txt").write_text("user", encoding="utf-8")
        with self.assertRaises(ValueError):
            synchronize(self.source, self.destination, self.record)
        self.assertEqual((self.destination / "notes.txt").read_text(), "user")

    def test_record_cannot_escape_the_skill_directory(self):
        self.adopt()
        value = json.loads(self.record.read_text())
        value["files"]["../../outside.txt"] = "a" * 64
        self.record.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            synchronize(self.source, self.destination, self.record)

    def test_untracked_installation_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            synchronize(self.source, self.destination, self.record)

    def test_source_destination_overlap_is_rejected(self):
        with self.assertRaises(ValueError):
            synchronize(self.source, self.source, self.record, adopt=True)

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            safe_child(self.destination, "../outside.txt")


if __name__ == "__main__":
    unittest.main()
