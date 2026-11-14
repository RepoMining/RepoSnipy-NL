"""Tests for service configuration that do not load the model or index."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from reposnipy_nl.service import (
    DEFAULT_DOMAIN_WEIGHTS,
    RepositoryService,
    _domain_weights_from_environment,
)


class ServiceConfigurationTests(unittest.TestCase):
    def test_resolve_mode_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as cache_dir:
            with patch.dict(
                os.environ,
                {"REPOSNIPY_CACHE_DIR": cache_dir},
                clear=False,
            ):
                service = RepositoryService()
                self.assertEqual(service.resolve_mode("repo"), "domain")
                self.assertEqual(service.resolve_mode(""), "domain")
                self.assertEqual(service.resolve_mode("default"), "domain")
                self.assertEqual(service.resolve_mode("doc"), "doc")

    def test_domain_weights_environment_override(self) -> None:
        with patch.dict(
            os.environ,
            {"REPOSNIPY_DOMAIN_WEIGHTS": "0.4,0.1,0.3,0.2"},
            clear=False,
        ):
            self.assertEqual(
                _domain_weights_from_environment(),
                {
                    "code": 0.4,
                    "doc": 0.1,
                    "readme": 0.3,
                    "requirement": 0.2,
                },
            )

    def test_invalid_domain_weights_fall_back_to_defaults(self) -> None:
        for configured in ("1,2", "a,b,c,d", "0,0,0,0"):
            with self.subTest(configured=configured):
                with patch.dict(
                    os.environ,
                    {"REPOSNIPY_DOMAIN_WEIGHTS": configured},
                    clear=False,
                ):
                    self.assertEqual(
                        _domain_weights_from_environment(),
                        DEFAULT_DOMAIN_WEIGHTS,
                    )

    def test_idle_metadata_does_not_require_assets(self) -> None:
        with tempfile.TemporaryDirectory() as cache_dir:
            with patch.dict(
                os.environ,
                {"REPOSNIPY_CACHE_DIR": cache_dir},
                clear=False,
            ):
                service = RepositoryService()
                metadata = service.metadata()
                self.assertEqual(metadata["status"], "idle")
                self.assertEqual(metadata["dataset"], "developing")


if __name__ == "__main__":
    unittest.main()
