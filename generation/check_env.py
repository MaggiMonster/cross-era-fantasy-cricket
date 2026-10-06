"""Check that PyTorch can use the Apple GPU (MPS) on this machine.

Usage, from the repo root:

    generation/.venv/bin/python -m generation.check_env
"""

from __future__ import annotations

import platform
import sys
import time

import torch

from generation.memlog import snapshot


def main() -> int:
    print(f"python   {platform.python_version()} ({platform.machine()})")
    print(f"torch    {torch.__version__}")
    print(f"mps      built={torch.backends.mps.is_built()} "
          f"available={torch.backends.mps.is_available()}")
    if not torch.backends.mps.is_available():
        print("FAIL: MPS is not available. Is this an arm64 Python on Apple Silicon?")
        return 1

    device = torch.device("mps")

    x = torch.randn(2048, 2048, device=device)
    start = time.time()
    value = (x @ x).sum().item()
    print(f"float32 matmul        ok ({time.time() - start:.2f} s)")
    if value != value:
        print("FAIL: matmul returned NaN")
        return 1

    # Half precision is what the diffusion model runs in.
    conv = torch.nn.Conv2d(64, 64, 3, padding=1).to(device, torch.float16)
    out = conv(torch.randn(1, 64, 64, 64, device=device, dtype=torch.float16))
    if not torch.isfinite(out).all():
        print("FAIL: float16 convolution produced non-finite values")
        return 1
    print("float16 convolution   ok")

    attn = torch.nn.functional.scaled_dot_product_attention(
        *(torch.randn(1, 8, 1024, 40, device=device, dtype=torch.float16) for _ in range(3))
    )
    if not torch.isfinite(attn).all():
        print("FAIL: float16 attention produced non-finite values")
        return 1
    print("float16 attention     ok")

    snap = snapshot()
    print(f"system RAM            {snap['system_total_mb'] / 1024:.1f} GB total, "
          f"{snap['system_available_mb'] / 1024:.1f} GB available")
    print(f"MPS recommended max   {torch.mps.recommended_max_memory() / 2**30:.1f} GB")
    print("OK: PyTorch MPS works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
