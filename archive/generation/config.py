"""Model choice and local paths for Part 2. See generation/README.md for the reasons."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = Path(__file__).resolve().parent / "models"  # git-ignored
OUTPUT_DIR = REPO_ROOT / "outputs" / "generation"  # git-ignored


@dataclass(frozen=True)
class ModelSpec:
    key: str
    repo_id: str
    allow_patterns: Tuple[str, ...]
    revision: Optional[str] = None

    @property
    def local_dir(self) -> Path:
        return MODELS_DIR / self.repo_id.split("/")[-1]


# Stable Diffusion 1.5 backbone, half-precision files only.
BASE = ModelSpec(
    key="base",
    repo_id="stable-diffusion-v1-5/stable-diffusion-v1-5",
    allow_patterns=(
        "model_index.json",
        "scheduler/*",
        "tokenizer/*",
        "text_encoder/config.json",
        "text_encoder/model.fp16.safetensors",
        "unet/config.json",
        "unet/diffusion_pytorch_model.fp16.safetensors",
        "vae/config.json",
        "vae/diffusion_pytorch_model.fp16.safetensors",
    ),
)

# AnimateDiff v3 temporal layers that turn the image model into a video model.
MOTION_ADAPTER = ModelSpec(
    key="motion_adapter",
    repo_id="guoyww/animatediff-motion-adapter-v1-5-3",
    allow_patterns=("config.json", "diffusion_pytorch_model.fp16.safetensors"),
)

# SparseCtrl RGB: conditions the clip on a still image (the image-to-video part).
SPARSECTRL_RGB = ModelSpec(
    key="sparsectrl_rgb",
    repo_id="guoyww/animatediff-sparsectrl-rgb",
    allow_patterns=("config.json", "diffusion_pytorch_model.fp16.safetensors"),
)

# Domain-adapter LoRA that SparseCtrl was trained alongside.
MOTION_LORA = ModelSpec(
    key="motion_lora",
    repo_id="guoyww/animatediff-motion-lora-v1-5-3",
    allow_patterns=("diffusion_pytorch_model.safetensors",),
)

ALL_MODELS = (BASE, MOTION_ADAPTER, SPARSECTRL_RGB, MOTION_LORA)
