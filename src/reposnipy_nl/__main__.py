"""Run the RepoSnipy-NL API with uvicorn."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "reposnipy_nl.api.app:app",
        host=os.environ.get("REPOSNIPY_HOST", "127.0.0.1"),
        port=int(os.environ.get("REPOSNIPY_PORT", "8000")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
