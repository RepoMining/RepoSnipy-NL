"""Pydantic request and response models for the RepoSnipy-NL API."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RepositoryCard(BaseModel):
    """Repository result returned by the search API."""

    name: str
    github_url: str
    stars: int = 0
    license: str = ""
    topics: List[str] = Field(default_factory=list)
    available_layers: List[str] = Field(default_factory=list)
    indexed: Optional[bool] = None
    score: Optional[float] = None


class RepositorySearchResponse(BaseModel):
    name: str
    mode: str
    limit: int
    query: RepositoryCard
    results: List[RepositoryCard]


class RequirementSearchRequest(BaseModel):
    """Request body for natural-language repository retrieval."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural-language software requirement.",
    )
    mode: str = Field(
        default="blend",
        description="Fusion mode: blend, readme, or doc.",
    )
    limit: int = Field(default=10, ge=1, le=100)


class RequirementSearchResponse(BaseModel):
    query: str
    normalized_query: str
    mode: str
    weights: Dict[str, float]
    results: List[RepositoryCard]


class IndexRequest(BaseModel):
    """Request body for encoding and indexing a repository."""

    name: str = Field(..., description="GitHub repository in owner/repo form.")
    github_token: Optional[str] = Field(
        default=None,
        description="Optional GitHub token used only for this request.",
    )


class IndexResponse(BaseModel):
    name: str


class LayerInfo(BaseModel):
    key: str
    field: str
    dim: int
    covered: int
    total: int
    ratio: float


class MetaResponse(BaseModel):
    status: str
    message: str
    dataset: str
    error: Optional[str] = None
    index_size: Optional[int] = None
    raw_index_size: Optional[int] = None
    load_seconds: Optional[float] = None
    layers: Optional[List[LayerInfo]] = None
    samples: Optional[List[str]] = None
    device: Optional[str] = None
    default_mode: Optional[str] = None
    domain_weights: Optional[Dict[str, float]] = None
    drop_components: Optional[int] = None
