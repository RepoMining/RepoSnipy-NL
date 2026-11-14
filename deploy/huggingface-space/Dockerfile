# syntax=docker/dockerfile:1

FROM node:20.19-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN python -m pip install --upgrade pip \
    && python -m pip install -e ".[api]"

COPY --from=frontend /build/frontend/dist ./frontend/dist

RUN mkdir -p data .cache \
    && curl --fail --location --retry 3 --output data/index.bin \
       "https://media.githubusercontent.com/media/RepoMining/RepoSnipy/a8ea0df92e4143c008be2878f8ddae98ab8eb201/data/index.bin" \
    && echo "3837b4cb3f10cd0ff035201ef44ab655608b2877e5c89efc5cc63a69b666c415  data/index.bin" \
       | sha256sum --check -

ENV REPOSNIPY_PROJECT_ROOT=/app \
    REPOSNIPY_DATASET=product \
    REPOSNIPY_INDEX_PATH=/app/data/index.bin \
    REPOSNIPY_CACHE_DIR=/app/.cache \
    REPOSNIPY_HOST=0.0.0.0 \
    REPOSNIPY_PORT=7860

EXPOSE 7860

CMD ["python", "-m", "reposnipy_nl"]
