"""Repository index loading and retrieval service."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np

from common.repo_doc import RepoDoc
from reposnipy_nl.retrieval import (
    ChannelSpace,
    DEFAULT_MAX_CHARS,
    DEFAULT_MAX_LENGTH,
    RequirementRetriever,
    preprocess_channel,
    transform_query_vector,
)

CHANNELS: Mapping[str, str] = {
    "code": "code_embedding",
    "doc": "doc_embedding",
    "readme": "readme_embedding",
    "requirement": "requirement_embedding",
}
CHANNEL_KEYS = tuple(CHANNELS)
DEFAULT_DOMAIN_MODE = "domain"
DEFAULT_DOMAIN_WEIGHTS = {
    "code": 0.45,
    "doc": 0.05,
    "readme": 0.40,
    "requirement": 0.10,
}
CURATED_SAMPLES = (
    "numpy/numpy",
    "psf/requests",
    "django/django",
    "pytorch/pytorch",
    "huggingface/transformers",
    "tiangolo/fastapi",
    "pallets/flask",
    "scikit-learn/scikit-learn",
)


def _environment_path(name: str) -> Optional[Path]:
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser().resolve() if value else None


def _domain_weights_from_environment() -> dict[str, float]:
    configured = os.environ.get("REPOSNIPY_DOMAIN_WEIGHTS", "").strip()
    if not configured:
        return dict(DEFAULT_DOMAIN_WEIGHTS)
    try:
        values = [float(value) for value in configured.split(",")]
    except ValueError:
        return dict(DEFAULT_DOMAIN_WEIGHTS)
    if len(values) != len(CHANNEL_KEYS) or sum(values) <= 0:
        return dict(DEFAULT_DOMAIN_WEIGHTS)
    return dict(zip(CHANNEL_KEYS, values))


class PipelineQueryEncoder:
    """Adapt the RepoSim4Py pipeline to the retrieval encoder protocol."""

    def __init__(self, service: "RepositoryService") -> None:
        self._service = service

    def encode(self, text: str, *, max_length: int = 512) -> Any:
        import torch

        pipeline = self._service.get_pipeline()
        with self._service.pipeline_lock:
            with torch.no_grad():
                vector = pipeline.encode(text, max_length=max_length)
        if hasattr(vector, "detach"):
            vector = vector.detach()
        if hasattr(vector, "cpu"):
            vector = vector.cpu()
        if hasattr(vector, "numpy"):
            vector = vector.numpy()
        return np.asarray(vector, dtype=np.float32).reshape(-1)


class RepositoryService:
    """Load a repository index and expose retrieval operations."""

    def __init__(
        self,
        *,
        index_path: Optional[Path] = None,
        models_dir: Optional[Path] = None,
        dataset: Optional[str] = None,
        drop_components: Optional[int] = None,
    ) -> None:
        project_root = Path(
            os.environ.get(
                "REPOSNIPY_PROJECT_ROOT",
                Path(__file__).resolve().parents[2],
            )
        )
        self.project_root = project_root
        self.dataset = (
            dataset
            or os.environ.get("REPOSNIPY_DATASET", "developing")
        ).strip().lower()
        suffix = "" if self.dataset == "product" else "_developing"
        self.index_path = (
            index_path
            or _environment_path("REPOSNIPY_INDEX_PATH")
            or self.project_root / "data" / f"index{suffix}.bin"
        )
        self.models_dir = (
            models_dir
            or _environment_path("REPOSNIPY_MODELS_DIR")
            or self.project_root / "models"
        )
        self.cache_dir = (
            _environment_path("REPOSNIPY_CACHE_DIR")
            or self.project_root / ".cache"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.cache_dir / "huggingface"))
        os.environ.setdefault(
            "HF_MODULES_CACHE",
            str(self.cache_dir / "huggingface" / "modules"),
        )
        self.model_path = self.models_dir / "RepoSim4Py"
        self.drop_components = int(
            drop_components
            if drop_components is not None
            else os.environ.get("REPOSNIPY_DROP_COMPONENTS", "8")
        )
        self.domain_weights = _domain_weights_from_environment()

        self.lock = threading.RLock()
        self.pipeline_lock = threading.RLock()
        self.state: dict[str, Any] = {
            "state": "idle",
            "message": "Waiting for initialization",
            "error": None,
            "loaded_at": None,
            "load_seconds": None,
        }
        self.index = None
        self.documents: list[RepoDoc] = []
        self.by_name: dict[str, RepoDoc] = {}
        self.index_of: dict[str, int] = {}
        self.features: dict[str, dict[str, Any]] = {}
        self.pipeline = None

    def load(self) -> None:
        """Load the index and prepare normalized channel matrices."""

        from docarray.index import InMemoryExactNNIndex

        with self.lock:
            self.state.update(
                state="loading",
                message="Loading repository index",
                error=None,
            )
        started = time.time()
        try:
            index = InMemoryExactNNIndex[RepoDoc](
                index_file_path=self.index_path
            )
            by_name: dict[str, RepoDoc] = {}
            documents: list[RepoDoc] = []
            for document in index._docs:
                if document.name in by_name:
                    continue
                by_name[document.name] = document
                documents.append(document)

            features: dict[str, dict[str, Any]] = {}
            for key, field_name in CHANNELS.items():
                matrix = np.zeros((len(documents), 768), dtype=np.float32)
                mask = np.zeros(len(documents), dtype=bool)
                for row, document in enumerate(documents):
                    value = getattr(document, field_name, None)
                    if value is None:
                        continue
                    matrix[row] = np.asarray(value, dtype=np.float32).reshape(-1)
                    mask[row] = True
                unit_matrix, mean, projection = preprocess_channel(
                    matrix,
                    mask,
                    drop_components=self.drop_components,
                )
                features[key] = {
                    "matrix": unit_matrix,
                    "mask": mask,
                    "mean": mean,
                    "projection": projection,
                }

            with self.lock:
                self.index = index
                self.documents = documents
                self.by_name = by_name
                self.index_of = {
                    document.name: row
                    for row, document in enumerate(documents)
                }
                self.features = features
                self.state.update(
                    state="ready",
                    message=f"Loaded {len(documents)} repositories",
                    loaded_at=time.time(),
                    load_seconds=round(time.time() - started, 2),
                )
        except Exception as exc:  # noqa: BLE001
            with self.lock:
                self.state.update(
                    state="error",
                    message="Initialization failed",
                    error=f"{type(exc).__name__}: {exc}",
                )
            raise

    def require_ready(self) -> None:
        if self.state["state"] == "error":
            raise RuntimeError(self.state["error"] or "Initialization failed")
        if self.state["state"] != "ready":
            raise RuntimeError("Repository index is still loading")

    def get_pipeline(self):
        """Load RepoSim4Py lazily because model initialization is expensive."""

        with self.lock:
            if self.pipeline is None:
                from transformers import pipeline

                model = (
                    str(self.model_path)
                    if self.model_path.exists()
                    else "Henry65/RepoSim4Py"
                )
                if self.model_path.exists():
                    os.environ.setdefault("HF_HUB_OFFLINE", "1")
                self.pipeline = pipeline(
                    model=model,
                    trust_remote_code=True,
                    device_map="auto",
                )
            return self.pipeline

    @staticmethod
    def repository_payload(document: RepoDoc) -> dict[str, Any]:
        available = [
            channel
            for channel, field_name in CHANNELS.items()
            if getattr(document, field_name, None) is not None
        ]
        return {
            "name": document.name,
            "github_url": f"https://github.com/{document.name}",
            "stars": int(document.stars or 0),
            "license": (document.license or "").strip(),
            "topics": list(document.topics or []),
            "available_layers": available,
        }

    def get_repository(self, name: str) -> Optional[dict[str, Any]]:
        self.require_ready()
        document = self.by_name.get(name)
        if document is None:
            return None
        payload = self.repository_payload(document)
        payload["indexed"] = True
        return payload

    def metadata(self) -> dict[str, Any]:
        if self.state["state"] != "ready":
            return {
                "status": self.state["state"],
                "message": self.state["message"],
                "error": self.state["error"],
                "dataset": self.dataset,
            }

        layers = []
        for key, field_name in CHANNELS.items():
            feature = self.features[key]
            covered = int(feature["mask"].sum())
            layers.append(
                {
                    "key": key,
                    "field": field_name,
                    "dim": int(feature["matrix"].shape[1]),
                    "covered": covered,
                    "total": len(self.documents),
                    "ratio": round(covered / max(len(self.documents), 1), 4),
                }
            )

        samples = [
            name for name in CURATED_SAMPLES if name in self.by_name
        ]
        if len(samples) < 6:
            for document in sorted(
                self.documents, key=lambda item: -(item.stars or 0)
            ):
                if document.name not in samples:
                    samples.append(document.name)
                if len(samples) >= 8:
                    break

        return {
            "status": "ready",
            "message": self.state["message"],
            "dataset": self.dataset,
            "index_size": len(self.documents),
            "raw_index_size": len(self.index._docs),
            "load_seconds": self.state["load_seconds"],
            "layers": layers,
            "samples": samples,
            "device": self.device(),
            "default_mode": DEFAULT_DOMAIN_MODE,
            "domain_weights": self.domain_weights,
            "drop_components": self.drop_components,
        }

    @staticmethod
    def device() -> str:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            return "mps"
        return "cpu"

    def resolve_mode(self, mode: Optional[str]) -> str:
        value = (mode or DEFAULT_DOMAIN_MODE).strip().lower()
        if value in ("", "default", "repo"):
            return DEFAULT_DOMAIN_MODE
        return value

    def search(
        self,
        name: str,
        mode: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        self.require_ready()
        limit = max(1, min(int(limit), 100))
        resolved = self.resolve_mode(mode)
        if resolved == DEFAULT_DOMAIN_MODE:
            return self._search_domain(name, limit)
        return self._search_channel(name, resolved, limit)

    def _search_domain(self, name: str, limit: int) -> list[dict[str, Any]]:
        query_index = self.index_of.get(name)
        if query_index is None:
            raise KeyError(name)

        fused = np.zeros(len(self.documents), dtype=np.float32)
        for channel in CHANNEL_KEYS:
            weight = self.domain_weights.get(channel, 0.0)
            if weight <= 0:
                continue
            feature = self.features[channel]
            scores = feature["matrix"] @ feature["matrix"][query_index]
            scores[~feature["mask"]] = 0.0
            fused += weight * scores
        fused[query_index] = -np.inf
        return self._rank_documents(fused, query_name=name, limit=limit)

    def _search_channel(
        self,
        name: str,
        channel: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        if channel not in CHANNELS:
            raise ValueError(f"Unknown retrieval channel: {channel}")
        query_index = self.index_of.get(name)
        if query_index is None:
            raise KeyError(name)

        feature = self.features[channel]
        if not feature["mask"][query_index]:
            return []
        scores = feature["matrix"] @ feature["matrix"][query_index]
        scores[~feature["mask"]] = 0.0
        scores[query_index] = -np.inf
        return self._rank_documents(scores, query_name=name, limit=limit)

    def _rank_documents(
        self,
        scores: np.ndarray,
        *,
        query_name: Optional[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        order = np.argsort(-scores, kind="stable")
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index in order:
            document = self.documents[int(index)]
            if document.name == query_name or document.name in seen:
                continue
            seen.add(document.name)
            payload = self.repository_payload(document)
            payload["score"] = float(scores[int(index)])
            results.append(payload)
            if len(results) >= limit:
                break
        return results

    def _requirement_spaces(self) -> dict[str, ChannelSpace]:
        spaces = {}
        for channel in ("readme", "doc"):
            feature = self.features[channel]
            spaces[channel] = ChannelSpace(
                matrix=feature["matrix"],
                mask=feature["mask"],
                mean=feature["mean"],
                projection=feature["projection"],
            )
        return spaces

    def search_requirement(
        self,
        text: str,
        mode: str = "blend",
        limit: int = 10,
        *,
        max_chars: int = DEFAULT_MAX_CHARS,
        max_length: int = DEFAULT_MAX_LENGTH,
    ) -> dict[str, Any]:
        self.require_ready()
        retriever = RequirementRetriever(
            repository_names=[document.name for document in self.documents],
            channel_spaces=self._requirement_spaces(),
            encoder=PipelineQueryEncoder(self),
            max_chars=max_chars,
            max_length=max_length,
        )
        result = retriever.search(text, mode=mode, limit=limit)
        results = []
        for hit in result.hits:
            document = self.by_name[hit.repository]
            payload = self.repository_payload(document)
            payload["score"] = hit.score
            results.append(payload)
        return {
            "query": result.query,
            "normalized_query": result.normalized_query,
            "mode": result.mode,
            "weights": dict(result.weights),
            "results": results,
        }

    def encode_repository(
        self,
        name: str,
        github_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fetch and encode one repository through RepoSim4Py."""

        pipeline = self.get_pipeline()
        extracted = pipeline.preprocess(name, github_token=github_token)
        if not extracted:
            raise ValueError(
                "Repository was not found or the GitHub request failed"
            )
        repository = pipeline.forward(extracted)[0]

        def clean(value: Any) -> Optional[np.ndarray]:
            array = np.asarray(value)
            return None if np.all(array == 0) else array.reshape(-1)

        return {
            "name": repository.get("name") or name,
            "topics": list(repository.get("topics") or []),
            "stars": int(repository.get("stars") or 0),
            "license": (repository.get("license") or "").strip(),
            "embeddings": {
                "code_embedding": clean(repository["mean_code_embedding"]),
                "doc_embedding": clean(repository["mean_doc_embedding"]),
                "readme_embedding": clean(repository["mean_readme_embedding"]),
                "requirement_embedding": clean(
                    repository["mean_requirement_embedding"]
                ),
                "repository_embedding": clean(
                    repository["mean_repo_embedding"]
                ),
            },
        }

    def persist_repository(self, encoded: Mapping[str, Any]) -> dict[str, str]:
        """Persist an encoded repository and update in-memory features."""

        self.require_ready()
        if not encoded["license"]:
            raise ValueError("Repository without a license cannot be indexed")
        meaningful = [
            value
            for key, value in encoded["embeddings"].items()
            if key in CHANNELS.values() and value is not None
        ]
        if not meaningful:
            raise ValueError("No valid repository content was extracted")

        document = self.by_name.get(encoded["name"])
        is_new = document is None
        if document is None:
            document = RepoDoc(
                name=encoded["name"],
                topics=[],
                stars=0,
                license="",
                code_embedding=None,
                doc_embedding=None,
                readme_embedding=None,
                requirement_embedding=None,
                repository_embedding=None,
            )

        document.name = encoded["name"]
        document.topics = encoded["topics"]
        document.stars = encoded["stars"]
        document.license = encoded["license"]
        for field_name, value in encoded["embeddings"].items():
            setattr(document, field_name, value)

        with self.lock:
            if is_new:
                self.index.index(document)
            self.index.persist(str(self.index_path))

            if is_new:
                self.documents.append(document)
            self.by_name = {
                item.name: item for item in self.documents
            }
            self.index_of = {
                item.name: row for row, item in enumerate(self.documents)
            }
            row = self.index_of[document.name]
            for channel, field_name in CHANNELS.items():
                feature = self.features[channel]
                matrix = feature["matrix"]
                if row >= len(matrix):
                    matrix = np.vstack(
                        [
                            matrix,
                            np.zeros(
                                (1, matrix.shape[1]),
                                dtype=np.float32,
                            ),
                        ]
                    )
                    feature["matrix"] = matrix
                    feature["mask"] = np.append(feature["mask"], False)
                value = getattr(document, field_name, None)
                if value is None:
                    matrix[row] = 0.0
                    feature["mask"][row] = False
                else:
                    matrix[row] = transform_query_vector(
                        value,
                        ChannelSpace(
                            matrix=matrix,
                            mask=feature["mask"],
                            mean=feature["mean"],
                            projection=feature["projection"],
                        ),
                    )
                    feature["mask"][row] = True

        return {"name": document.name}
