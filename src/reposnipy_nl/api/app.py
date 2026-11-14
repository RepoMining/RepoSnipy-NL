"""FastAPI application for repository and natural-language retrieval."""

from __future__ import annotations

import mimetypes
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from reposnipy_nl.api.schemas import (
    IndexRequest,
    IndexResponse,
    MetaResponse,
    RepositoryCard,
    RepositorySearchResponse,
    RequirementSearchRequest,
    RequirementSearchResponse,
)
from reposnipy_nl.service import RepositoryService

mimetypes.init()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("font/woff2", ".woff2")

service = RepositoryService()
FRONTEND_DIST = service.project_root / "frontend" / "dist"

PLACEHOLDER = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>RepoSnipy-NL API</title></head>
<body style="font-family:system-ui;background:#0b0f19;color:#e6edf7;padding:48px">
  <h1>RepoSnipy-NL API</h1>
  <p>The web interface has not been built yet.</p>
  <p><a style="color:#5eead4" href="/docs">Open the API documentation</a></p>
</body>
</html>"""


def translate_error(callable_: Callable[..., Any], *args: Any, **kwargs: Any):
    """Translate service failures into HTTP responses."""

    try:
        return callable_(*args, **kwargs)
    except HTTPException:
        raise
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Repository is not in the index: {exc.args[0]}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def create_app(repository_service: RepositoryService | None = None) -> FastAPI:
    """Create an application with optional dependency injection for tests."""

    active_service = repository_service or service

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if active_service.state["state"] == "idle":
            threading.Thread(
                target=active_service.load,
                daemon=True,
            ).start()
        yield

    application = FastAPI(
        title="RepoSnipy-NL API",
        description=(
            "Natural-language and repository-to-repository retrieval over "
            "precomputed RepoSim4Py embeddings."
        ),
        version="0.3.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health", summary="Health check")
    def health():
        return {
            "status": "ok",
            "engine": active_service.state["state"],
        }

    @application.get(
        "/api/meta",
        response_model=MetaResponse,
        summary="Index metadata and initialization state",
    )
    def metadata():
        return active_service.metadata()

    @application.get(
        "/api/repo",
        response_model=RepositoryCard,
        summary="Look up an indexed repository",
    )
    def repository(name: str = Query(..., description="owner/repo")):
        payload = translate_error(active_service.get_repository, name)
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"Repository is not indexed: {name}",
            )
        return payload

    @application.get(
        "/api/search",
        response_model=RepositorySearchResponse,
        summary="Repository-to-repository search",
    )
    def search(
        name: str = Query(..., description="owner/repo"),
        mode: str = Query(
            "domain",
            description="domain, code, doc, readme, or requirement",
        ),
        limit: int = Query(10, ge=1, le=100),
    ):
        query_repository = translate_error(
            active_service.get_repository, name
        )
        if query_repository is None:
            raise HTTPException(
                status_code=404,
                detail=f"Repository is not indexed: {name}",
            )
        resolved = active_service.resolve_mode(mode)
        results = translate_error(
            active_service.search, name, resolved, limit
        )
        return {
            "name": name,
            "mode": resolved,
            "limit": limit,
            "query": query_repository,
            "results": results,
        }

    @application.post(
        "/api/search/requirement",
        response_model=RequirementSearchResponse,
        summary="Natural-language repository retrieval",
    )
    def search_requirement(
        payload: RequirementSearchRequest = Body(...),
    ):
        return translate_error(
            active_service.search_requirement,
            payload.query,
            payload.mode,
            payload.limit,
        )

    @application.post(
        "/api/index",
        response_model=IndexResponse,
        summary="Encode and persist a repository",
    )
    def index_repository(payload: IndexRequest = Body(...)):
        encoded = translate_error(
            active_service.encode_repository,
            payload.name,
            payload.github_token,
        )
        return translate_error(active_service.persist_repository, encoded)

    if (FRONTEND_DIST / "index.html").is_file():
        application.mount(
            "/",
            StaticFiles(directory=str(FRONTEND_DIST), html=True),
            name="frontend",
        )
    else:
        @application.get(
            "/",
            response_class=HTMLResponse,
            include_in_schema=False,
        )
        def placeholder():
            return PLACEHOLDER

    return application


app = create_app()
