"""Unit tests for query-time channel fusion and ranking."""

from __future__ import annotations

import unittest

import numpy as np

from reposnipy_nl.retrieval import (
    DEFAULT_REQUIREMENT_WEIGHTS,
    ChannelSpace,
    RequirementRetriever,
    fuse_requirement_scores,
    normalize_requirement,
    preprocess_channel,
    transform_query_vector,
)


class StaticEncoder:
    """Return a fixed vector and record calls made by the retriever."""

    def __init__(self, vector) -> None:
        self.vector = np.asarray(vector, dtype=np.float32)
        self.calls: list[tuple[str, int]] = []

    def encode(self, text: str, *, max_length: int = 512):
        self.calls.append((text, max_length))
        return self.vector


def make_space(
    matrix,
    *,
    mask=None,
    mean=None,
    projection=None,
) -> ChannelSpace:
    values = np.asarray(matrix, dtype=np.float32)
    rows, dimensions = values.shape
    return ChannelSpace(
        matrix=values,
        mask=(
            np.ones(rows, dtype=bool)
            if mask is None
            else np.asarray(mask, dtype=bool)
        ),
        mean=(
            np.zeros(dimensions, dtype=np.float32)
            if mean is None
            else np.asarray(mean, dtype=np.float32)
        ),
        projection=(
            np.eye(dimensions, dtype=np.float32)
            if projection is None
            else np.asarray(projection, dtype=np.float32)
        ),
    )


class RetrievalTests(unittest.TestCase):
    def test_normalize_requirement_collapses_whitespace(self) -> None:
        self.assertEqual(
            normalize_requirement("  extract\n tables\tfrom PDFs  "),
            "extract tables from PDFs",
        )

    def test_normalize_requirement_rejects_empty_and_long_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            normalize_requirement(" \n\t ")
        with self.assertRaisesRegex(ValueError, "character limit"):
            normalize_requirement("123456", max_chars=5)

    def test_query_vector_uses_persisted_mean_and_projection(self) -> None:
        space = make_space(
            [[1.0, 0.0], [0.0, 1.0]],
            mean=[1.0, 2.0],
            projection=np.diag([1.0, 2.0]),
        )
        transformed = transform_query_vector([3.0, 4.0], space)
        expected = np.asarray([2.0, 4.0], dtype=np.float32)
        expected /= np.linalg.norm(expected)
        np.testing.assert_allclose(transformed, expected, rtol=1e-6)

    def test_channel_preprocessing_normalizes_only_available_rows(self) -> None:
        matrix = np.asarray(
            [
                [1.0, 2.0],
                [3.0, 5.0],
                [99.0, 99.0],
            ],
            dtype=np.float32,
        )
        transformed, mean, projection = preprocess_channel(
            matrix,
            np.asarray([True, True, False]),
            drop_components=0,
        )
        np.testing.assert_allclose(
            np.linalg.norm(transformed[:2], axis=1),
            np.ones(2),
            rtol=1e-6,
        )
        np.testing.assert_array_equal(transformed[2], np.zeros(2))
        np.testing.assert_allclose(
            mean,
            np.asarray([[2.0, 3.5]], dtype=np.float32),
        )
        np.testing.assert_allclose(
            projection,
            np.eye(2),
            atol=1e-6,
        )

    def test_fusion_renormalizes_missing_channels_per_repository(self) -> None:
        readme = make_space(
            [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            mask=[True, True, False],
        )
        doc = make_space(
            [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            mask=[True, False, True],
        )
        fused = fuse_requirement_scores(
            {
                "readme": np.asarray([0.9, 0.9, 0.9], dtype=np.float32),
                "doc": np.asarray([0.2, 0.2, 0.2], dtype=np.float32),
            },
            {"readme": readme, "doc": doc},
            {"readme": 0.4, "doc": 0.6},
        )
        np.testing.assert_allclose(
            fused,
            np.asarray([0.48, 0.9, 0.2], dtype=np.float32),
        )

    def test_fusion_rejects_unknown_channel(self) -> None:
        space = make_space([[1.0, 0.0]])
        with self.assertRaisesRegex(ValueError, "missing score or space"):
            fuse_requirement_scores(
                {"readme": np.asarray([1.0])},
                {"readme": space},
                {"unknown": 1.0},
            )

    def test_retriever_encodes_once_and_ranks_limit(self) -> None:
        readme = make_space(
            [
                [1.0, 0.0],
                [0.8, 0.6],
                [0.0, 1.0],
            ]
        )
        doc = make_space(
            [
                [0.0, 1.0],
                [0.6, 0.8],
                [1.0, 0.0],
            ]
        )
        encoder = StaticEncoder([1.0, 0.0])
        retriever = RequirementRetriever(
            ["example/readme", "example/both", "example/doc"],
            {"readme": readme, "doc": doc},
            encoder,
            max_length=256,
        )

        result = retriever.search(
            "  find a useful package ",
            mode="blend",
            limit=2,
        )

        self.assertEqual(result.normalized_query, "find a useful package")
        self.assertEqual(
            [hit.repository for hit in result.hits],
            ["example/doc", "example/both"],
        )
        self.assertEqual(encoder.calls, [("find a useful package", 256)])
        self.assertEqual(dict(result.weights), {"readme": 0.33, "doc": 0.67})

    def test_single_channel_modes_use_only_requested_channel(self) -> None:
        readme = make_space(
            [
                [1.0, 0.0],
                [0.8, 0.6],
                [0.0, 1.0],
            ]
        )
        doc = make_space(
            [
                [0.0, 1.0],
                [0.6, 0.8],
                [1.0, 0.0],
            ]
        )
        names = ["readme-first", "middle", "doc-first"]
        retriever = RequirementRetriever(
            names,
            {"readme": readme, "doc": doc},
            StaticEncoder([1.0, 0.0]),
        )

        readme_result = retriever.search("query", mode="readme", limit=3)
        doc_result = retriever.search("query", mode="doc", limit=3)

        self.assertEqual(
            [hit.repository for hit in readme_result.hits],
            ["readme-first", "middle", "doc-first"],
        )
        self.assertEqual(
            [hit.repository for hit in doc_result.hits],
            ["doc-first", "middle", "readme-first"],
        )

    def test_invalid_mode_and_limit_are_rejected(self) -> None:
        space = make_space([[1.0, 0.0]])
        retriever = RequirementRetriever(
            ["example/repo"],
            {"readme": space, "doc": space},
            StaticEncoder([1.0, 0.0]),
        )
        with self.assertRaisesRegex(ValueError, "unknown requirement"):
            retriever.search("query", mode="code")
        with self.assertRaisesRegex(ValueError, "limit must be positive"):
            retriever.search("query", limit=0)

    def test_default_weights_sum_to_one(self) -> None:
        self.assertAlmostEqual(
            sum(DEFAULT_REQUIREMENT_WEIGHTS["blend"].values()),
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
