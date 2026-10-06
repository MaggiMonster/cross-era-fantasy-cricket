"""Compare each model component on CPU (float32) against MPS (float32 and float16).

Use this when the output looks wrong, to rule the Apple GPU and half precision
in or out. Every line should show a relative difference well under 0.01.

Usage, from the repo root:

    generation/.venv/bin/python -m generation.check_components
"""

from __future__ import annotations

import sys

import torch
from diffusers import (
    AutoencoderKL,
    MotionAdapter,
    SparseControlNetModel,
    UNet2DConditionModel,
    UNetMotionModel,
)
from diffusers.utils import logging
from transformers import CLIPTextModel

from generation.config import BASE, MOTION_ADAPTER, SPARSECTRL_RGB

FRAMES, LATENT = 8, 32  # 8 frames at 256x256
TOLERANCE = 0.01
worst = 0.0


def compare(name: str, ref: torch.Tensor, out: torch.Tensor) -> None:
    global worst
    ref, out = ref.float().cpu(), out.float().cpu()
    rel = ((ref - out).abs().mean() / ref.abs().mean()).item()
    finite = bool(torch.isfinite(out).all())
    worst = max(worst, rel if finite else float("inf"))
    print(f"{name:<26} rel diff={rel:.4f}  finite={finite}", flush=True)


@torch.no_grad()
def main() -> int:
    logging.set_verbosity_error()
    mps, half = "mps", torch.float16
    g = torch.Generator().manual_seed(0)
    latents = torch.randn(1, 4, FRAMES, LATENT, LATENT, generator=g)
    # The pipeline repeats the prompt embedding once per frame.
    embeds = torch.randn(1, 77, 768, generator=g).repeat(FRAMES, 1, 1)
    t = torch.tensor([500])

    text = CLIPTextModel.from_pretrained(BASE.local_dir, subfolder="text_encoder", variant="fp16", dtype=torch.float32).eval()
    ids = torch.randint(0, 49407, (1, 77), generator=g)
    ref = text(ids)[0]
    compare("text encoder  mps f32", ref, text.to(mps)(ids.to(mps))[0])
    compare("text encoder  mps f16", ref, text.to(mps, half)(ids.to(mps))[0])
    del text

    vae = AutoencoderKL.from_pretrained(BASE.local_dir, subfolder="vae", variant="fp16", torch_dtype=torch.float32).eval()
    x = torch.randn(2, 4, LATENT, LATENT, generator=g)
    ref = vae.decode(x).sample
    compare("vae decode    mps f32", ref, vae.to(mps).decode(x.to(mps)).sample)
    compare("vae decode    mps f16", ref, vae.to(mps, half).decode(x.to(mps, half)).sample)
    del vae

    unet2d = UNet2DConditionModel.from_pretrained(BASE.local_dir, subfolder="unet", variant="fp16", torch_dtype=torch.float32)
    adapter = MotionAdapter.from_pretrained(MOTION_ADAPTER.local_dir, variant="fp16", torch_dtype=torch.float32)
    unet = UNetMotionModel.from_unet2d(unet2d, adapter).eval()
    del unet2d, adapter
    ref = unet(latents, t, encoder_hidden_states=embeds).sample
    compare("motion unet   mps f32", ref, unet.to(mps)(latents.to(mps), t.to(mps), encoder_hidden_states=embeds.to(mps)).sample)
    compare("motion unet   mps f16", ref, unet.to(mps, half)(latents.to(mps, half), t.to(mps), encoder_hidden_states=embeds.to(mps, half)).sample)
    del unet
    torch.mps.empty_cache()

    ctrl = SparseControlNetModel.from_pretrained(SPARSECTRL_RGB.local_dir, variant="fp16", torch_dtype=torch.float32).eval()
    cond = torch.randn(1, 4, FRAMES, LATENT, LATENT, generator=g)
    mask = torch.zeros(1, 1, FRAMES, LATENT, LATENT)
    mask[:, :, 0] = 1
    down_ref, mid_ref = ctrl(latents, t, encoder_hidden_states=embeds, controlnet_cond=cond, conditioning_mask=mask, return_dict=False)
    ctrl.to(mps)
    down, mid = ctrl(latents.to(mps), t.to(mps), encoder_hidden_states=embeds.to(mps), controlnet_cond=cond.to(mps), conditioning_mask=mask.to(mps), return_dict=False)
    compare("sparsectrl mid   mps f32", mid_ref, mid)
    compare("sparsectrl down  mps f32", down_ref[-1], down[-1])

    ok = worst < TOLERANCE
    print(f"{'OK' if ok else 'FAIL'}: worst relative difference {worst:.4f} (tolerance {TOLERANCE})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
