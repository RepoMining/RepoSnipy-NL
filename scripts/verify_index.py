"""Download or verify the pinned RepoSnipy-NL vector index."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "release" / "index_manifest.json"
DEFAULT_URL = (
    "https://github.com/RepoMining/RepoSnipy-NL/releases/download/"
    "v1.0.0/index.bin"
)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def verify_file(path: Path, manifest: dict) -> None:
    expected_size = int(manifest["asset"]["size_bytes"])
    expected_sha256 = manifest["asset"]["sha256"].lower()
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise RuntimeError(
            f"index size mismatch: expected {expected_size}, got {actual_size}"
        )

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            "index checksum mismatch: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )


def download(url: str, output: Path, manifest: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + ".part")
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "RepoSnipy-NL-index-downloader"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            with partial.open("wb") as handle:
                while chunk := response.read(1024 * 1024):
                    handle.write(chunk)
        verify_file(partial, manifest)
        os.replace(partial, output)
    finally:
        if partial.exists():
            partial.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download or verify the pinned RepoSnipy-NL vector index."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the release asset before verification.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Release asset URL.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "index.bin",
        help="Destination or existing index path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    output = args.output.resolve()
    if args.download:
        download(args.url, output, manifest)
    elif not output.is_file():
        raise FileNotFoundError(f"index does not exist: {output}")
    else:
        verify_file(output, manifest)
    print(f"Verified {output} ({manifest['asset']['size_bytes']} bytes)")
    print(f"SHA-256 {manifest['asset']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
