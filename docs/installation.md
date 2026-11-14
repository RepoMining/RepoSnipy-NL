# Installation

RepoSnipy-NL has a small core package and optional API dependencies. The model,
repository index, and compiled frontend are intentionally not committed to Git.

## Prerequisites

- Python 3.10 or 3.11. Python 3.10 is the primary tested version.
- Node.js `^20.19.0` or `>=22.12.0` and npm when building the web interface.
- Enough disk space and memory for the RepoSim4Py model and repository index.

## Core package

### Linux or macOS

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

The core installation supports vector fusion and the offline Demo. It does not
install PyTorch, Transformers, DocArray, FastAPI, or the frontend toolchain.

## Full API installation

Install the optional API dependencies:

```bash
python -m pip install -e ".[api]"
```

The default index lives at:

```text
data/index_developing.bin
```

The local RepoSim4Py model can be placed at:

```text
models/RepoSim4Py/
```

If the local model directory is absent, the service attempts to load
`Henry65/RepoSim4Py` through Transformers and therefore needs model access.
Model weights, indexes, caches, and secrets must remain outside Git.

The following environment variables are supported:

| Variable | Purpose |
| --- | --- |
| `REPOSNIPY_PROJECT_ROOT` | Project root used for default data, model, and frontend paths |
| `REPOSNIPY_INDEX_PATH` | Explicit repository index path |
| `REPOSNIPY_MODELS_DIR` | Directory containing `RepoSim4Py` |
| `REPOSNIPY_DATASET` | `developing` (default) or `product` |
| `REPOSNIPY_CACHE_DIR` | Writable Hugging Face and runtime cache directory |
| `REPOSNIPY_DROP_COMPONENTS` | Leading principal directions removed during channel preprocessing |
| `REPOSNIPY_DOMAIN_WEIGHTS` | Four comma-separated domain weights |
| `REPOSNIPY_HOST` | API bind host, default `127.0.0.1` |
| `REPOSNIPY_PORT` | API port, default `8000` |

For a product index named `data/index.bin`, set:

```bash
export REPOSNIPY_DATASET=product
```

On Windows PowerShell:

```powershell
$env:REPOSNIPY_DATASET = "product"
```

## Frontend

Install locked dependencies and build static assets:

```bash
cd frontend
npm ci
npm run build
cd ..
```

The build is written to `frontend/dist`. When `frontend/dist/index.html`
exists, the FastAPI service serves the compiled application at `/`.

For frontend development, run the backend in one terminal and Vite in another:

```bash
python -m reposnipy_nl
```

```bash
cd frontend
npm run dev
```

Vite runs at `http://localhost:5173` and proxies `/api` to
`http://127.0.0.1:8000` by default. Set `VITE_API_TARGET` before starting Vite
to use a different backend address.

## Verify the installation

The offline Demo and tests require no model or repository index:

```bash
python examples/retrieval_demo.py
python -m unittest discover -s tests -v
```

Audit the frozen benchmark:

```bash
python evaluation/audit_benchmark.py
```

Start the complete local service:

```bash
python -m reposnipy_nl
```

Then open `http://127.0.0.1:8000/` for the web interface or
`http://127.0.0.1:8000/docs` for the API documentation.

## Troubleshooting

- `503 Service Unavailable` usually means the index is still loading or failed
  to initialize. Check the server log and `/api/meta`.
- A missing local model may trigger a remote model download. Set
  `REPOSNIPY_MODELS_DIR` to an existing local model directory for offline use.
- The placeholder page appears when `frontend/dist/index.html` has not been
  built. Run `npm run build` in `frontend`.
- Use a writable `REPOSNIPY_CACHE_DIR` when the project directory is read-only.
