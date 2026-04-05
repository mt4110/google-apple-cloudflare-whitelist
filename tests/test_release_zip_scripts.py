from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from replace_zip_contents import detect_root_dir_name, replace_zip_contents


class ReplaceZipContentsTests(unittest.TestCase):
    def test_detect_root_dir_name_ignores_top_level_metadata_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_zip = Path(tmp) / "base.zip"
            with zipfile.ZipFile(base_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("release-root/README.md", "old")
                archive.writestr("SHA256SUMS", "checksum")

            self.assertEqual(detect_root_dir_name(base_zip), "release-root")

    def test_replace_zip_contents_preserves_non_project_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_zip = Path(tmp) / "base.zip"
            source_dir = Path(tmp) / "working-tree"
            output_zip = Path(tmp) / "output.zip"

            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "README.md").write_text("new", encoding="utf-8")

            with zipfile.ZipFile(base_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("release-root/README.md", "old")
                archive.writestr("SHA256SUMS", "checksum")

            replace_zip_contents(base_zip=base_zip, source_dir=source_dir, output_path=output_zip)

            with zipfile.ZipFile(output_zip) as archive:
                names = set(archive.namelist())
                self.assertIn("release-root/README.md", names)
                self.assertIn("SHA256SUMS", names)
                self.assertNotIn("working-tree/README.md", names)
                self.assertEqual(archive.read("release-root/README.md").decode("utf-8"), "new")
                self.assertEqual(archive.read("SHA256SUMS").decode("utf-8"), "checksum")

    def test_replace_zip_contents_rejects_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_zip = Path(tmp) / "base.zip"
            source_dir = Path(tmp) / "working-tree"
            output_zip = Path(tmp) / "output.zip"

            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "README.md").write_text("new", encoding="utf-8")

            with zipfile.ZipFile(base_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("../escape.txt", "oops")

            with self.assertRaises(ValueError):
                replace_zip_contents(base_zip=base_zip, source_dir=source_dir, output_path=output_zip)
