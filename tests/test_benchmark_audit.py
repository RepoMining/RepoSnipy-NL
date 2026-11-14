"""Integration test for the frozen benchmark audit."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = PROJECT_ROOT / "evaluation" / "audit_benchmark.py"


class BenchmarkAuditTests(unittest.TestCase):
    def test_audit_recomputes_the_frozen_weight_grid(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            check=False,
            timeout=60,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["weight_grid_points"], 101)
        self.assertEqual(
            payload["weight_grid_metric_values_recomputed"],
            1212,
        )
        self.assertEqual(payload["selected"]["readme"], 0.33)
        self.assertEqual(payload["selected"]["doc"], 0.67)


if __name__ == "__main__":
    unittest.main()
