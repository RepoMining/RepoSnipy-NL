# RepoSnipy-NL

**Natural-language repository retrieval for the RepoSnipy ecosystem.**

RepoSnipy-NL is an experimental extension of
[RepoMining/RepoSnipy](https://github.com/RepoMining/RepoSnipy). It lets a user
describe a software requirement in natural language and retrieve relevant
Python repositories from precomputed RepoSim4Py embeddings.

The project is being developed incrementally under the RepoMining organization.
The initial repository stage contains project documentation, licensing, and the
English Python package structure only. Retrieval functionality will be migrated
in subsequent commits.

## Scope

- Accept either an indexed `owner/repo` identifier or a natural-language query.
- Encode a requirement once with the existing RepoSim4Py pipeline.
- Reuse persisted README and docstring embeddings without rebuilding the corpus.
- Apply channel-specific normalization and weighted cosine ranking.
- Renormalize only over channels available for each candidate.
- Preserve the existing repository-to-repository search workflow.

## Planned structure

```text
RepoSnipy-NL/
├── src/reposnipy_nl/     Python package
├── tests/                Automated tests
├── backend/              FastAPI service
├── frontend/             Vue 3 web interface
├── evaluation/           Reproducible retrieval evaluation
├── docs/                 Installation and deployment documentation
└── README.md
```

Directories that contain implementation code will be added in later stages.

## Project status

Initial project structure and documentation. The repository is not yet a
runnable application.

## Relationship to RepoSnipy

This repository is an experimental extension maintained by the RepoMining
community. The original WebPro prototype and its implementation history are
available at
[dyb158507/RepoSnipy-WebPro](https://github.com/dyb158507/RepoSnipy-WebPro).

The project reuses and extends the open-source RepoSnipy and RepoSim4Py
ecosystem. Upstream model weights, extraction pipelines, datasets, and original
application code remain attributed to their respective authors.

## Maintainership and contributions

The project is currently led by [@dyb158507](https://github.com/dyb158507), with
technical guidance and review from RepoMining maintainers. Contributions should
preserve upstream attribution and follow the repository's MIT license.

## License

This project is distributed under the [MIT License](LICENSE).
