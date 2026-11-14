# RepoSnipy-NL web interface

Vue 3 and Vite frontend for repository-to-repository and natural-language
repository retrieval.

## Development

Start the FastAPI service from the repository root:

```bash
.venv/bin/python -m reposnipy_nl
```

Start the Vite development server in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The application is available at `http://localhost:5173`. Vite proxies `/api/*`
to `http://127.0.0.1:8000`. Set `VITE_API_TARGET` when the backend uses a
different address.

## Production build

```bash
cd frontend
npm run build
```

The build is written to `frontend/dist`. When `dist/index.html` exists, the
FastAPI service mounts the compiled frontend at `/`.

## Structure

```text
src/
  api.js                    API client and input normalization
  App.vue                   Page state and search workflow
  styles/main.css           Theme and component styles
  components/
    AppHeader.vue           Branding, index status, and theme control
    HeroSearch.vue          Search input, examples, and index statistics
    RepoSummary.vue         Metadata and channel availability
    ModeTabs.vue            Repository retrieval channels
    RequirementModeTabs.vue Natural-language fusion channels
    ResultList.vue          Loading, error, and ranked result states
    ResultCard.vue          Individual repository result
    IndexDialog.vue         Repository encoding dialog
```

## Behavior

- Supports `owner/repo`, GitHub URLs, and natural-language requirements.
- Uses URL fragments to preserve shareable search state.
- Supports light and dark themes with a local preference.
- Detects backend disconnection and retries automatically.
