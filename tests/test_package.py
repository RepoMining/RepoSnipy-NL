"""Package metadata tests."""

from __future__ import annotations

import re
import json
import unittest
from pathlib import Path

import reposnipy_nl

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_runtime_version_matches_project_metadata(self) -> None:
        project_text = (PROJECT_ROOT / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        match = re.search(
            r'(?m)^version\s*=\s*"([^"]+)"',
            project_text,
        )
        self.assertIsNotNone(match)
        self.assertEqual(
            reposnipy_nl.__version__,
            match.group(1),
        )
        frontend = json.loads(
            (PROJECT_ROOT / "frontend" / "package.json").read_text(
                encoding="utf-8"
            )
        )
        manifest = json.loads(
            (PROJECT_ROOT / "release" / "index_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(frontend["version"], reposnipy_nl.__version__)
        self.assertEqual(manifest["release"], "v1.0.0")
        self.assertEqual(
            manifest["asset"]["sha256"],
            "3837b4cb3f10cd0ff035201ef44ab655608b2877e5c89efc5cc63a69b666c415",
        )


if __name__ == "__main__":
    unittest.main()
