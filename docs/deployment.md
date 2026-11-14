# Deployment

## Deployment readiness

The repository does not contain the 226 MB vector index or the RepoSim4Py model.
A complete deployment needs:

1. the `v1.0.0` release index;
2. access to `Henry65/RepoSim4Py`, or a local copy of the model;
3. writable model cache storage;
4. enough memory and disk space for PyTorch, the model, and the index.

GitHub Pages is not used because it can only host static files and cannot run
the FastAPI backend. The repository currently has no Pages site configured.

## Hugging Face Space

The `deploy/huggingface-space/` directory contains a Docker Space bundle. Its
build stage compiles the Vue interface, while the runtime downloads the exact
pinned index from the upstream public Git LFS object and verifies its SHA-256.

The deployment workflow is manual and requires:

- a Hugging Face write token stored as the `HF_TOKEN` Actions secret;
- a target Space id supplied when dispatching the workflow.

From GitHub Actions, run **Deploy Hugging Face Space**, enter a Space id such as
`owner/RepoSnipy-NL`, and start the workflow. The workflow creates the Docker
Space if necessary and uploads the deployment bundle.

After deployment, the public URL follows this pattern:

```text
https://huggingface.co/spaces/<owner>/<space-name>
```

The first model request may take longer while Transformers downloads and
initializes RepoSim4Py. Do not describe a Space as live until the workflow has
completed and the URL has been checked.

## Direct server deployment

For a regular server:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[api]"
python scripts/verify_index.py --download --output data/index.bin
export REPOSNIPY_DATASET=product
export REPOSNIPY_HOST=0.0.0.0
python -m reposnipy_nl
```

Place a TLS reverse proxy in front of the service for public deployments, and
make `REPOSNIPY_CACHE_DIR` point to persistent writable storage.
