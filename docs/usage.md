# Usage

## Python library

The retriever accepts precomputed README and docstring channel matrices. Each
channel stores a repository matrix, availability mask, mean vector, and
projection matrix.

```python
from reposnipy_nl import ChannelSpace, RequirementRetriever

retriever = RequirementRetriever(
    repository_names=names,
    channel_spaces={
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
    },
    encoder=encoder,
)

result = retriever.search(
    "Extract tables from PDF files and export them as CSV",
    mode="blend",
    limit=10,
)
for hit in result.hits:
    print(hit.repository, hit.score)
```

`encoder` must expose an `encode(text, max_length=512)` method compatible with
the RepoSim4Py pipeline. The query is encoded once. Its vector is transformed
separately with each channel's stored mean and projection.

For a dependency-free local example using synthetic vectors, run:

```bash
python examples/retrieval_demo.py
```

The Demo is illustrative only; it is not an experimental result.

## Retrieval modes

| Mode | Behavior |
| --- | --- |
| `blend` | README `0.33` plus docstring `0.67`, normalized over available channels |
| `readme` | README channel only |
| `doc` | Docstring channel only |

If one channel is unavailable for a candidate, the production blend
renormalizes over the remaining channel. A missing README does not automatically
exclude a repository with a usable docstring.

## HTTP API

Start the server and check readiness:

```bash
python -m reposnipy_nl
```

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/meta
```

Search by an indexed repository:

```bash
curl "http://127.0.0.1:8000/api/search?name=numpy%2Fnumpy&mode=domain&limit=10"
```

Search by a natural-language requirement:

```bash
curl -X POST "http://127.0.0.1:8000/api/search/requirement" \
  -H "Content-Type: application/json" \
  -d '{"query":"Extract tables from PDF files and export them as CSV","mode":"blend","limit":10}'
```

The requirement endpoint has these limits:

- non-empty query;
- at most 500 characters;
- `mode` is `blend`, `readme`, or `doc`;
- `limit` is between 1 and 100.

Example response:

```json
{
  "query": "Extract tables from PDF files and export them as CSV",
  "normalized_query": "Extract tables from PDF files and export them as CSV",
  "mode": "blend",
  "weights": {
    "readme": 0.33,
    "doc": 0.67
  },
  "results": [
    {
      "name": "owner/repository",
      "github_url": "https://github.com/owner/repository",
      "stars": 0,
      "license": "MIT",
      "topics": [],
      "available_layers": ["readme", "doc"],
      "score": 0.0
    }
  ]
}
```

## Web interface

The unified search box accepts:

- `owner/repo`;
- a GitHub repository URL;
- a natural-language requirement.

After a requirement search, switch between blended, README-only, and
docstring-only ranking. Result cards expose the repository URL, available
channels, stars, topics, license, and normalized score bars.

## Index a repository through the API

With a configured model and writable index:

```bash
curl -X POST "http://127.0.0.1:8000/api/index" \
  -H "Content-Type: application/json" \
  -d '{"name":"owner/repository","github_token":null}'
```

An optional GitHub token is used only for that request and is not persisted by
this project.
