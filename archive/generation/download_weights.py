"""Download the model weights into generation/models/ (git-ignored).

Only the half-precision files the pipeline needs are fetched, about 4.7 GB in
total. Re-running skips files that are already complete.

Usage, from the repo root:

    generation/.venv/bin/python -m generation.download_weights
"""

from __future__ import annotations

import sys

from huggingface_hub import snapshot_download

from generation.config import ALL_MODELS, MODELS_DIR


def dir_size_mb(path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 2**20


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    total = 0.0
    for spec in ALL_MODELS:
        print(f"{spec.key}: {spec.repo_id} -> {spec.local_dir}", flush=True)
        snapshot_download(
            repo_id=spec.repo_id,
            revision=spec.revision,
            allow_patterns=list(spec.allow_patterns),
            local_dir=spec.local_dir,
        )
        size = dir_size_mb(spec.local_dir)
        total += size
        print(f"  {size:,.0f} MB on disk", flush=True)
    print(f"Done. {total / 1024:.1f} GB in {MODELS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
