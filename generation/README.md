# generation/

Part 2: pre-trained image-to-video diffusion model, run locally on Apple Silicon.
Input motion comes from pose files described in
[`docs/interface.md`](../docs/interface.md).

**Status: partly working.** The environment, weights and a small run work; the
output is not yet usable. Read [`docs/m2-status.md`](../docs/m2-status.md) first.

## Setup

From the repo root. Needs Python 3.12 (`brew install python@3.12`); the system
Python 3.9 is too old for current PyTorch.

```sh
/opt/homebrew/bin/python3.12 -m venv generation/.venv
generation/.venv/bin/pip install -r generation/requirements.txt
generation/.venv/bin/python -m generation.check_env          # PyTorch MPS works?
generation/.venv/bin/python -m generation.download_weights   # about 4.6 GB
```

Weights go to `generation/models/`, which is git-ignored.

## Scripts

| Script | What it does |
|--------|--------------|
| `check_env.py` | Confirms PyTorch can use the Apple GPU (MPS), including half precision. |
| `download_weights.py` | Fetches only the half-precision files the pipeline needs. |
| `smoke_test.py` | Animates one still image and writes the clip plus a memory log to `outputs/generation/smoke/`. Options: `--image`, `--frames`, `--steps`, `--size`, `--dtype`, `--attention-slicing`. |
| `check_components.py` | Runs each model component on CPU and on MPS and compares the numbers. Use it to rule out the GPU or half precision when output looks wrong. |
| `memlog.py` | Memory logger used by the smoke test (process RAM, MPS tensors, MPS driver total). |
| `config.py` | Model repositories and local paths. |

```sh
generation/.venv/bin/python -m generation.smoke_test                       # 8 frames, about 30 s
generation/.venv/bin/python -m generation.smoke_test --frames 16 --steps 20  # slow, see status doc
generation/.venv/bin/python -m pytest tests/test_generation_memlog.py -q
```

Without `--image` the smoke test animates a synthetic placeholder figure, so it
needs no licensed photo.

## Model choice

**AnimateDiff v3 + SparseCtrl RGB on Stable Diffusion 1.5**, through `diffusers`.

| Part | Repository | Size on disk |
|------|-----------|--------------|
| Image backbone | `stable-diffusion-v1-5/stable-diffusion-v1-5` (fp16 files) | 2.0 GB |
| Motion layers | `guoyww/animatediff-motion-adapter-v1-5-3` | 1.6 GB |
| Still-image conditioning | `guoyww/animatediff-sparsectrl-rgb` | 0.9 GB |
| Adapter LoRA | `guoyww/animatediff-motion-lora-v1-5-3` | 0.1 GB |

Why this one:

- About 4.6 GB of weights in half precision, small enough to sit in 16 GB of
  shared memory. It is the only candidate we actually ran.
- Supported directly by `diffusers`, no custom build.
- Stable Diffusion 1.5 has OpenPose ControlNets, which is the route to pose
  conditioning in Milestone 3 (`docs/interface.md`, "Notes for Part 2").
- The base model is 512x512, our target size.

Alternatives from the proposal, judged on size and dependencies, **not tested**:

- **LTX-2**: far larger than 16 GB allows, even quantized.
- **MagicAnimate**: also Stable Diffusion 1.5 based, but needs DensePose
  (Detectron2), which is a heavy install on macOS, and is not in `diffusers`.
- **Stable Video Diffusion**: image-to-video, but no pose control and a heavier
  model at a higher native resolution.

Licences: Stable Diffusion 1.5 is CreativeML OpenRAIL-M. The AnimateDiff
repositories do not declare a licence on Hugging Face; check before publishing
anything beyond coursework.
