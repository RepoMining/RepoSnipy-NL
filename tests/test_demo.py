"""Smoke test for the synthetic retrieval demo."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = PROJECT_ROOT / "examples" / "retrieval_demo.py"


class DemoTests(unittest.TestCase):
    def test_demo_runs_without_model_or_index(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, str(DEMO_SCRIPT)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            check=False,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(
            "Synthetic in-memory demonstration; no model or index was loaded.",
            completed.stdout,
        )
        self.assertIn("example/pdf-reader", completed.stdout)


if __name__ == "__main__":
    unittest.main()
