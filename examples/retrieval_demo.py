"""Run the retrieval pipeline with synthetic, in-memory channel vectors."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_SRC = PROJECT_ROOT / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from reposnipy_nl import ChannelSpace, RequirementRetriever  # noqa: E402


REPOSITORIES = (
    "example/csv-exporter",
    "example/pdf-reader",
    "example/http-client",
)

README_VECTORS = np.asarray(
    [
        [1.0, 0.0, 0.0],
        [0.7071068, 0.7071068, 0.0],
        [0.0, 0.0, 1.0],
    ],
    dtype=np.float32,
)

DOC_VECTORS = np.asarray(
    [
        [0.6, 0.8, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ],
    dtype=np.float32,
)


class SyntheticEncoder:
    """Return a fixed query vector for an offline demonstration."""

    def encode(self, text: str, *, max_length: int = 512):
        del text, max_length
        return np.asarray([0.9, 0.1, 0.0], dtype=np.float32)


def make_space(matrix: np.ndarray) -> ChannelSpace:
    rows, dimensions = matrix.shape
    return ChannelSpace(
        matrix=matrix,
        mask=np.ones(rows, dtype=bool),
        mean=np.zeros(dimensions, dtype=np.float32),
        projection=np.eye(dimensions, dtype=np.float32),
    )


def main() -> int:
    retriever = RequirementRetriever(
        REPOSITORIES,
        {
            "readme": make_space(README_VECTORS),
            "doc": make_space(DOC_VECTORS),
        },
        SyntheticEncoder(),
    )
    query = "Extract tables from PDF files and export them as CSV"

    print("Synthetic in-memory demonstration; no model or index was loaded.")
    print(f"Query: {query}")
    for mode in ("blend", "readme", "doc"):
        result = retriever.search(query, mode=mode, limit=3)
        print(f"\nMode: {mode}")
        for rank, hit in enumerate(result.hits, start=1):
            print(f"  {rank}. {hit.repository:<24} score={hit.score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
