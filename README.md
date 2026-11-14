# RepoSnipy-NL

**Natural-language repository retrieval for the RepoSnipy ecosystem.**

RepoSnipy-NL is an experimental extension of
[RepoMining/RepoSnipy](https://github.com/RepoMining/RepoSnipy). It lets a user
describe a software requirement in natural language and retrieve relevant
Python repositories from precomputed RepoSim4Py embeddings.

The project is being developed incrementally under the RepoMining organization.
The Python package provides the core retrieval pipeline, a FastAPI service, a
Vue 3 web interface, and a reproducible retrieval benchmark.

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
├── src/reposnipy_nl/api/ FastAPI service
├── frontend/             Vue 3 web interface
├── evaluation/           Frozen benchmark and audit script
├── docs/                 Installation and deployment documentation
└── README.md
```

The documentation directory will be added in a later stage.

## Python library

```python
from reposnipy_nl import ChannelSpace, RequirementRetriever

spaces = {
    "readme": ChannelSpace(
        matrix=readme_matrix,
        mask=readme_available,
        mean=readme_mean,
        projection=readme_projection,
    ),
    "doc": ChannelSpace(
        matrix=doc_matrix,
        mask=doc_available,
        mean=doc_mean,
        projection=doc_projection,
    ),
}

retriever = RequirementRetriever(
    repository_names=repository_names,
    channel_spaces=spaces,
    encoder=reposim4py_pipeline,
)
response = retriever.search(
    "Extract tables from PDF files and export them as CSV",
    mode="blend",
    limit=10,
)
```

The default `blend` weights are README `0.33` and docstring `0.67`, selected on
validation data. Missing channels are renormalized per repository so a missing
README or docstring does not exclude an otherwise valid candidate.

## Evaluation

The repository includes one frozen benchmark with 40 functional intents, 80
Chinese and English queries, and 2,706 query-repository judgments. Run the
independent data-integrity and metric audit with:

```bash
python evaluation/audit_benchmark.py
```

The script verifies the benchmark checksum, reconstructs all 101 fusion-weight
points, and checks the production README/docstring ratio. Its results apply to
closed-pool reranking over the benchmark candidate union, not full-index
recall. See [evaluation/README.md](evaluation/README.md) for the protocol,
metrics, and limitations.

## Project status

Core retrieval logic is available as a Python library. The FastAPI service,
Vue 3 web interface, and reproducible benchmark are ready for direct use.

## Running the API

Install the API dependencies from a source checkout:

```bash
python -m venv .venv
.venv/bin/pip install -e ".[api]"
```

Prepare the index and model outside Git:

```text
data/index_developing.bin
models/RepoSim4Py/
```

The backend uses `.cache/huggingface` inside the project by default for model
metadata. Set `REPOSNIPY_CACHE_DIR` to use another writable cache location.

Start the service:

```bash
.venv/bin/python -m reposnipy_nl
```

The API listens on `http://127.0.0.1:8000` by default. OpenAPI documentation is
available at `/docs`.

For the frontend development server, run:

```bash
cd frontend
npm install
npm run dev
```

The Vite server runs at `http://localhost:5173` and proxies API requests to the
FastAPI service. For a production-style local run:

```bash
cd frontend
npm run build
cd ..
.venv/bin/python -m reposnipy_nl
```

FastAPI then serves the compiled interface at `/`.

Available endpoints:

- `GET /api/health`
- `GET /api/meta`
- `GET /api/repo`
- `GET /api/search`
- `POST /api/search/requirement`
- `POST /api/index`

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
