# Release assets

Large model indexes are distributed as GitHub Release assets rather than source
files. `release/index_manifest.json` pins the source repository, upstream
commit, byte size, SHA-256, and validated repository counts.

The `v1.0.0` index is the upstream RepoSim4Py-compatible `data/index.bin` from
commit `a8ea0df92e4143c008be2878f8ddae98ab8eb201`. It is not re-encoded by
RepoSnipy-NL.

After the GitHub Release workflow completes, download it with the URL documented
in `docs/installation.md`, or run:

```bash
python scripts/verify_index.py --download --output data/index.bin
```

Use the product dataset setting:

```bash
export REPOSNIPY_DATASET=product
```
