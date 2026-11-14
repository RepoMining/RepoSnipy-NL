"""RepoSnipy-NL natural-language repository retrieval package."""

from reposnipy_nl.retrieval import (
    DEFAULT_REQUIREMENT_WEIGHTS,
    ChannelSpace,
    RequirementRetriever,
    RequirementSearchHit,
    RequirementSearchResult,
    fuse_requirement_scores,
    normalize_requirement,
    preprocess_channel,
    transform_query_vector,
)

__version__ = "0.3.0"

__all__ = [
    "DEFAULT_REQUIREMENT_WEIGHTS",
    "ChannelSpace",
    "RequirementRetriever",
    "RequirementSearchHit",
    "RequirementSearchResult",
    "fuse_requirement_scores",
    "normalize_requirement",
    "preprocess_channel",
    "transform_query_vector",
]
