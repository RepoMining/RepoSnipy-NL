"""Natural-language retrieval over precomputed repository channel embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

import numpy as np

DEFAULT_REQUIREMENT_WEIGHTS: Mapping[str, Mapping[str, float]] = MappingProxyType(
    {
        "blend": MappingProxyType({"readme": 0.33, "doc": 0.67}),
        "readme": MappingProxyType({"readme": 1.0}),
        "doc": MappingProxyType({"doc": 1.0}),
    }
)
DEFAULT_MODE = "blend"
DEFAULT_MAX_CHARS = 500
DEFAULT_MAX_LENGTH = 512
DEFAULT_DROP_COMPONENTS = 8


class QueryEncoder(Protocol):
    """Minimal RepoSim4Py-compatible encoder interface."""

    def encode(self, text: str, *, max_length: int = 512) -> Any:
        """Encode text into a one-dimensional vector-like object."""


@dataclass(frozen=True)
class ChannelSpace:
    """A precomputed repository channel with its query-time transformation."""

    matrix: np.ndarray
    mask: np.ndarray
    mean: np.ndarray
    projection: np.ndarray

    def __post_init__(self) -> None:
        matrix = np.asarray(self.matrix, dtype=np.float32)
        mask = np.asarray(self.mask, dtype=bool)
        mean = np.asarray(self.mean, dtype=np.float32).reshape(-1)
        projection = np.asarray(self.projection, dtype=np.float32)

        if matrix.ndim != 2:
            raise ValueError("channel matrix must be two-dimensional")
        if mask.ndim != 1 or len(mask) != len(matrix):
            raise ValueError("channel mask must match the matrix row count")
        if mean.shape != (matrix.shape[1],):
            raise ValueError("channel mean must match the embedding dimension")
        if projection.shape != (matrix.shape[1], matrix.shape[1]):
            raise ValueError("channel projection must be square")

        object.__setattr__(self, "matrix", matrix)
        object.__setattr__(self, "mask", mask)
        object.__setattr__(self, "mean", mean)
        object.__setattr__(self, "projection", projection)


@dataclass(frozen=True)
class RequirementSearchHit:
    """One ranked repository result."""

    repository: str
    score: float


@dataclass(frozen=True)
class RequirementSearchResult:
    """Structured response for a natural-language requirement query."""

    query: str
    normalized_query: str
    mode: str
    weights: Mapping[str, float]
    hits: tuple[RequirementSearchHit, ...]


def preprocess_channel(
    matrix: np.ndarray,
    mask: np.ndarray,
    *,
    drop_components: int = DEFAULT_DROP_COMPONENTS,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Center, remove leading principal directions, and L2-normalize a channel."""

    values = np.asarray(matrix, dtype=np.float32)
    available = np.asarray(mask, dtype=bool)
    if values.ndim != 2 or available.ndim != 1 or len(values) != len(available):
        raise ValueError("matrix and mask dimensions do not match")
    if not available.any():
        raise ValueError("channel has no available vectors")
    if drop_components < 0:
        raise ValueError("drop_components must be non-negative")

    subset = values[available]
    mean = subset.mean(axis=0, keepdims=True)
    centered = subset - mean
    covariance = centered.T @ centered / max(len(subset) - 1, 1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance.astype(np.float64))
    vectors = eigenvectors[:, np.argsort(-eigenvalues)]
    keep = np.ones(vectors.shape[1], dtype=np.float64)
    keep[: min(drop_components, len(keep))] = 0.0
    projection = ((vectors * keep) @ vectors.T).astype(np.float32)

    transformed = values.copy()
    transformed[available] = centered @ projection
    norms = np.linalg.norm(transformed, axis=1, keepdims=True)
    transformed = transformed / np.maximum(norms, 1e-9)
    transformed[~available] = 0.0
    return transformed, mean.astype(np.float32), projection


def transform_query_vector(
    vector: Any,
    space: ChannelSpace,
) -> np.ndarray:
    """Apply the persisted channel mean and projection to a query vector."""

    if hasattr(vector, "detach"):
        vector = vector.detach()
    if hasattr(vector, "cpu"):
        vector = vector.cpu()
    if hasattr(vector, "numpy"):
        vector = vector.numpy()

    transformed = np.asarray(vector, dtype=np.float32).reshape(-1) - space.mean
    transformed = transformed @ space.projection
    norm = float(np.linalg.norm(transformed))
    if norm > 1e-9:
        transformed = transformed / norm
    return transformed.astype(np.float32, copy=False)


def normalize_requirement(
    text: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """Collapse whitespace and enforce the public query length limit."""

    normalized = " ".join((text or "").split())
    if not normalized:
        raise ValueError("requirement text must not be empty")
    if len(normalized) > max_chars:
        raise ValueError(
            f"requirement text exceeds the {max_chars}-character limit"
        )
    return normalized


def resolve_requirement_weights(
    mode: str | None,
    weights_by_mode: Mapping[str, Mapping[str, float]] = DEFAULT_REQUIREMENT_WEIGHTS,
) -> tuple[str, dict[str, float]]:
    """Resolve and validate a named fusion configuration."""

    resolved = (mode or DEFAULT_MODE).strip().lower()
    if resolved in ("", "default"):
        resolved = DEFAULT_MODE
    if resolved not in weights_by_mode:
        raise ValueError(f"unknown requirement retrieval mode: {resolved}")

    configured_weights = {
        key: float(value) for key, value in weights_by_mode[resolved].items()
    }
    if any(value < 0 for value in configured_weights.values()):
        raise ValueError("requirement retrieval weights must be non-negative")
    weights = {
        key: value for key, value in configured_weights.items() if value > 0
    }
    if not weights:
        raise ValueError("requirement retrieval mode has no positive weights")
    return resolved, weights


def fuse_requirement_scores(
    channel_scores: Mapping[str, np.ndarray],
    channel_spaces: Mapping[str, ChannelSpace],
    weights: Mapping[str, float],
) -> np.ndarray:
    """Fuse channel scores and renormalize over available channels per row."""

    numerator: np.ndarray | None = None
    denominator: np.ndarray | None = None

    for channel, weight in weights.items():
        if weight <= 0:
            continue
        if channel not in channel_scores or channel not in channel_spaces:
            raise ValueError(f"missing score or space for channel: {channel}")

        scores = np.asarray(channel_scores[channel], dtype=np.float32)
        available = channel_spaces[channel].mask
        if scores.ndim != 1 or len(scores) != len(available):
            raise ValueError(f"invalid score vector for channel: {channel}")

        if numerator is None:
            numerator = np.zeros_like(scores)
            denominator = np.zeros_like(scores)

        numerator += weight * np.where(available, scores, 0.0)
        denominator += weight * available

    if numerator is None or denominator is None:
        raise ValueError("at least one positive channel weight is required")

    safe_denominator = np.maximum(denominator, 1e-12)
    return np.where(
        denominator > 0,
        numerator / safe_denominator,
        -np.inf,
    ).astype(np.float32, copy=False)


class RequirementRetriever:
    """Rank repositories for natural-language requirements."""

    def __init__(
        self,
        repository_names: Sequence[str],
        channel_spaces: Mapping[str, ChannelSpace],
        encoder: QueryEncoder,
        *,
        weights_by_mode: Mapping[str, Mapping[str, float]] =
            DEFAULT_REQUIREMENT_WEIGHTS,
        max_chars: int = DEFAULT_MAX_CHARS,
        max_length: int = DEFAULT_MAX_LENGTH,
    ) -> None:
        self.repository_names = tuple(repository_names)
        self.channel_spaces = dict(channel_spaces)
        self.encoder = encoder
        self.weights_by_mode = weights_by_mode
        self.max_chars = max_chars
        self.max_length = max_length

        if not self.repository_names:
            raise ValueError("at least one repository is required")
        for channel, space in self.channel_spaces.items():
            if len(space.matrix) != len(self.repository_names):
                raise ValueError(
                    f"channel {channel} row count does not match repositories"
                )

    def search(
        self,
        text: str,
        *,
        mode: str = DEFAULT_MODE,
        limit: int = 10,
    ) -> RequirementSearchResult:
        """Encode one requirement and return ranked repositories."""

        normalized = normalize_requirement(text, max_chars=self.max_chars)
        resolved, weights = resolve_requirement_weights(
            mode, self.weights_by_mode
        )
        limit = int(limit)
        if limit < 1:
            raise ValueError("limit must be positive")

        query_vector = self.encoder.encode(
            normalized, max_length=self.max_length
        )
        channel_scores: dict[str, np.ndarray] = {}
        for channel in weights:
            if channel not in self.channel_spaces:
                raise ValueError(f"missing channel space: {channel}")
            space = self.channel_spaces[channel]
            transformed = transform_query_vector(query_vector, space)
            channel_scores[channel] = space.matrix @ transformed

        fused = fuse_requirement_scores(
            channel_scores, self.channel_spaces, weights
        )
        order = np.argsort(-fused, kind="stable")[: min(limit, len(fused))]
        hits = tuple(
            RequirementSearchHit(
                repository=self.repository_names[int(index)],
                score=float(fused[int(index)]),
            )
            for index in order
            if np.isfinite(fused[int(index)])
        )
        return RequirementSearchResult(
            query=(text or "").strip(),
            normalized_query=normalized,
            mode=resolved,
            weights=MappingProxyType(weights),
            hits=hits,
        )
