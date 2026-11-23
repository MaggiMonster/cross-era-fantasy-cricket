"""Tiny image-to-video smoke test with memory logging.

Loads the chosen model (AnimateDiff v3 + SparseCtrl RGB on Stable Diffusion 1.5),
animates one still image for a handful of frames at low resolution, checks the
result is a real video (finite, not blank, actually moving) and writes the clip
plus a memory log to outputs/generation/smoke/.

This is deliberately small. 512x512 for 3-5 seconds is Turn 4.

Known issue (docs/m2-status.md): with the default 8 frames the run completes and
frame 0 matches the input, but the later frames are abstract patterns. 16 frames
gives a coherent clip but is slow and close to the memory limit on 16 GB.

Usage, from the repo root:

    generation/.venv/bin/python -m generation.smoke_test
    generation/.venv/bin/python -m generation.smoke_test --image path/to/player.jpg
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from generation.config import (
    ALL_MODELS,
    BASE,
    MOTION_ADAPTER,
    MOTION_LORA,
    OUTPUT_DIR,
    SPARSECTRL_RGB,
)
from generation.memlog import MemoryLogger

DEFAULT_PROMPT = "a cricketer in white flannels playing a shot, vintage photograph"
DEFAULT_NEGATIVE = "low quality, blurry, deformed, extra limbs"


def placeholder_image(size: int) -> Image.Image:
    """Synthetic stand-in for a player photo: a plain figure on a sepia field.

    Placeholder only, so the smoke test needs no downloaded or licensed image.
    """
    img = Image.new("RGB", (size, size), (196, 170, 128))
    draw = ImageDraw.Draw(img)
    s = size / 256
    draw.rectangle([0, 170 * s, size, size], fill=(120, 132, 84))
    white, skin = (238, 232, 214), (214, 170, 140)
    draw.ellipse([112 * s, 48 * s, 144 * s, 80 * s], fill=skin)
    draw.rectangle([104 * s, 82 * s, 152 * s, 150 * s], fill=white)
    draw.rectangle([106 * s, 150 * s, 124 * s, 214 * s], fill=white)
    draw.rectangle([132 * s, 150 * s, 150 * s, 214 * s], fill=white)
    draw.line([152 * s, 92 * s, 186 * s, 130 * s], fill=white, width=int(10 * s))
    draw.line([186 * s, 130 * s, 200 * s, 208 * s], fill=(150, 110, 60), width=int(8 * s))
    return img


def load_image(path: Path, size: int) -> Image.Image:
    """Centre-crop to a square and resize."""
    img = Image.open(path).convert("RGB")
    side = min(img.size)
    left, top = (img.width - side) // 2, (img.height - side) // 2
    return img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)


def check_frames(frames: np.ndarray) -> dict:
    """Sanity checks on (T, H, W, 3) uint8 output. Raises on a broken clip."""
    if not np.isfinite(frames).all():
        raise RuntimeError("output contains non-finite values")
    std = float(frames.std())
    motion = float(np.abs(np.diff(frames.astype(np.float32), axis=0)).mean())
    if std < 2.0:
        raise RuntimeError(f"output is blank (pixel std {std:.2f}); half precision may have overflowed")
    if motion < 0.05:
        raise RuntimeError(f"output does not move (mean frame difference {motion:.3f})")
    return {"pixel_std": round(std, 2), "mean_frame_diff": round(motion, 3)}


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--image", type=Path, help="still image to animate (default: synthetic placeholder)")
    p.add_argument("--prompt", default=DEFAULT_PROMPT)
    p.add_argument("--size", type=int, default=256, help="square output size in pixels")
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--fps", type=int, default=8)
    p.add_argument("--guidance", type=float, default=7.5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dtype", choices=("float16", "float32"), default="float16")
    p.add_argument("--attention-slicing", action="store_true",
                   help="compute attention in slices to lower peak memory (not yet tested, see docs/m2-status.md)")
    p.add_argument("--out", type=Path, default=OUTPUT_DIR / "smoke")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    missing = [m.local_dir for m in ALL_MODELS if not m.local_dir.exists()]
    if missing:
        print("Missing weights:", *missing, sep="\n  ")
        print("Run: generation/.venv/bin/python -m generation.download_weights")
        return 1

    import imageio.v2 as imageio
    import torch
    from diffusers import (
        AnimateDiffSparseControlNetPipeline,
        DPMSolverMultistepScheduler,
        MotionAdapter,
        SparseControlNetModel,
    )

    if not torch.backends.mps.is_available():
        print("MPS is not available; run generation.check_env")
        return 1
    device, dtype = "mps", getattr(torch, args.dtype)
    variant = "fp16"  # only half-precision files are downloaded; float32 upcasts them

    if args.image:
        image, image_source = load_image(args.image, args.size), args.image.name
    else:
        image, image_source = placeholder_image(args.size), "synthetic placeholder"

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = f"smoke_{args.size}px_{args.frames}f_{args.steps}s_{args.dtype}_{stamp}"

    with MemoryLogger() as mem:
        adapter = MotionAdapter.from_pretrained(MOTION_ADAPTER.local_dir, dtype=dtype, variant=variant)
        controlnet = SparseControlNetModel.from_pretrained(SPARSECTRL_RGB.local_dir, dtype=dtype, variant=variant)
        scheduler = DPMSolverMultistepScheduler.from_pretrained(
            BASE.local_dir,
            subfolder="scheduler",
            beta_schedule="linear",
            algorithm_type="dpmsolver++",
            use_karras_sigmas=True,
        )
        pipe = AnimateDiffSparseControlNetPipeline.from_pretrained(
            BASE.local_dir,
            motion_adapter=adapter,
            controlnet=controlnet,
            scheduler=scheduler,
            dtype=dtype,
            variant=variant,
            feature_extractor=None,  # optional, only used by IP-Adapter
            image_encoder=None,
        )
        pipe.load_lora_weights(
            MOTION_LORA.local_dir,
            weight_name="diffusion_pytorch_model.safetensors",
            adapter_name="motion_lora",
        )
        mem.mark("loaded on cpu")

        pipe.to(device)
        pipe.vae.enable_slicing()
        if args.attention_slicing:
            pipe.enable_attention_slicing()
        mem.mark("moved to mps")

        def on_step(_pipe, step, _timestep, kwargs):
            mem.mark(f"step {step + 1}/{args.steps}")
            return kwargs

        start = time.time()
        result = pipe(
            prompt=args.prompt,
            negative_prompt=DEFAULT_NEGATIVE,
            conditioning_frames=image,
            controlnet_frame_indices=[0],
            controlnet_conditioning_scale=1.0,
            num_frames=args.frames,
            height=args.size,
            width=args.size,
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
            generator=torch.Generator("cpu").manual_seed(args.seed),
            output_type="np",
            callback_on_step_end=on_step,
        )
        generate_s = time.time() - start
        mem.mark("generated")

        frames = (np.clip(result.frames[0], 0, 1) * 255).round().astype(np.uint8)
        checks = check_frames(frames)

        video_path = args.out / f"{name}.mp4"
        imageio.mimsave(video_path, list(frames), fps=args.fps, macro_block_size=1)
        image.save(args.out / f"{name}_input.png")

    log_path = mem.save(
        args.out / f"{name}.json",
        extra={
            "model": {m.key: m.repo_id for m in ALL_MODELS},
            "settings": {
                "size": args.size,
                "frames": args.frames,
                "steps": args.steps,
                "fps": args.fps,
                "guidance": args.guidance,
                "seed": args.seed,
                "dtype": args.dtype,
                "attention_slicing": args.attention_slicing,
                "device": device,
                "prompt": args.prompt,
                "image": image_source,
            },
            "torch": torch.__version__,
            "generate_s": round(generate_s, 1),
            "seconds_per_step": round(generate_s / args.steps, 2),
            "checks": checks,
            "video": video_path.name,
        },
    )

    peak = mem.peak
    print(f"\nOK  {frames.shape[0]} frames at {frames.shape[2]}x{frames.shape[1]} "
          f"in {generate_s:.0f} s ({generate_s / args.steps:.1f} s/step)")
    print(f"    checks: {checks}")
    print(f"    peak: rss {peak['rss_mb']:.0f} MB, mps tensors {peak['mps_allocated_mb']:.0f} MB, "
          f"mps driver {peak['mps_driver_mb']:.0f} MB, swap {peak['swap_used_mb']:.0f} MB")
    print("    These checks only catch blank or frozen output. Open the clip and look at it.")
    if args.frames < 16:
        print("    Note: below 16 frames AnimateDiff's later frames collapse into abstract "
              "patterns (docs/m2-status.md).")
    print(f"    video: {video_path}")
    print(f"    log:   {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
