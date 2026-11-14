# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-15

### Added

- Natural-language repository retrieval over precomputed RepoSim4Py channels.
- README and docstring channel projection with coverage-aware score fusion.
- FastAPI endpoints for repository search, requirement search, metadata, and
  repository indexing.
- Vue 3 web interface for repository identifiers, GitHub URLs, and natural
  language requirements.
- Frozen bilingual intent benchmark with 40 intents, 80 queries, and 2,706
  candidate judgments.
- Independent benchmark audit that recomputes 101 fusion-weight points.
- Installation, usage, deployment, testing, and offline Demo documentation.
- GitHub Release workflow and pinned vector-index manifest.

### Changed

- Production README/docstring weights are frozen at `0.33` / `0.67`, selected
  on the validation split.
- The Python package, API, and frontend versions are unified at `1.0.0`.

[1.0.0]: https://github.com/RepoMining/RepoSnipy-NL/releases/tag/v1.0.0
