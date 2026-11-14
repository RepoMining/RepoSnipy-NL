"""Package metadata tests."""

from __future__ import annotations

import re
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


if __name__ == "__main__":
    unittest.main()
