# Milestone 2 status (image-to-video)

Date: 2026-10-06. Author: Jaivin (Turn 2). **Partially done, deferred.**

In one line: the model is installed and runs on the MacBook, but we do not yet
have a usable clip. Short runs produce broken frames; a 16-frame run produces a
coherent clip but is too slow and too close to the memory limit, and it does not
keep the look of the input image.

## Setup

- MacBook Air M4, 16 GB shared memory, macOS 15.5. Python 3.12 (Homebrew),
  PyTorch 2.14.1 on MPS, `diffusers` 0.40.0. Exact versions in
  `generation/requirements.txt`.
- Model: AnimateDiff v3 motion layers + SparseCtrl RGB (still-image
  conditioning) on Stable Diffusion 1.5, half precision (float16). Reasons and
  alternatives in `generation/README.md`.
- Input image for all runs: the synthetic placeholder figure drawn by
  `generation/smoke_test.py` (flat colours, not a photo).
- Prompt: "a cricketer in white flannels playing a shot, vintage photograph".
  Guidance 7.5, seed 0.

## What works

- `generation/` venv, pinned requirements, weights (4.6 GB) downloaded to the
  git-ignored `generation/models/`.
- PyTorch MPS works, including float16 convolution and attention
  (`generation.check_env`).
- MPS and half precision are numerically correct. Every component (text
  encoder, VAE, motion UNet, SparseCtrl) gives the same output on MPS as on CPU:
  0.0% difference in float32, at most 0.2% in float16
  (`generation.check_components`).
- Plain Stable Diffusion 1.5 (no motion layers) renders a correct image on MPS
  in float16 (384x384, 15 steps).
- The motion adapter weights load completely (540 of 540 tensors, none missing).
- The image-to-video pipeline runs end to end and writes a clip and a memory log.
- Frame 0 of the output reproduces the input image, so the still-image
  conditioning is wired correctly.
- With 16 frames and 20 steps the later frames are a coherent, moving,
  vintage-looking scene of a player swinging (one run).

## Open problems

1. **Below 16 frames the later frames collapse.** With 8 frames, frame 0 is the
   input image and frames 1-7 are high-contrast abstract patterns. AnimateDiff
   is trained on 16-frame windows. The one 16-frame run was coherent, which
   supports this, but that run also used 20 steps instead of 8, so the two
   causes are not separated yet.
2. **16 frames at 256x256 is at the memory limit on this Mac.** One run finished
   but took 994 s (49.7 s per step) because the machine was swapping. A second
   attempt in a fresh process ran out of memory. The target is 60-100 frames at
   512x512.
3. **The clip does not keep the input image's appearance.** In the coherent
   16-frame run, frame 0 is the placeholder figure and frame 1 onwards is a
   different, prompt-driven scene. This may be because the placeholder is a flat
   drawing rather than a photo; not tested with a real photograph.
4. The smoke test's automatic checks (not blank, not frozen) passed on the
   broken clips. Clips have to be looked at.

## Everything tried

All at 256x256 on MPS. "cn" is the still-image conditioning strength.

| # | Frames | Steps | Precision | Scheduler | cn | Result |
|---|--------|-------|-----------|-----------|----|--------|
| 1 | 8 | 8 | float16 | DPM++ Karras | 1 | Frame 0 = input, frames 1-7 abstract patterns |
| 2 | 8 | 8 | float32 | DPM++ Karras | 1 | Same broken output as #1, so not a half-precision problem. 10x slower |
| 3 | 8 | 8 | float16 | DPM++ Karras | 0 | All frames abstract patterns (no image conditioning at all) |
| 4 | 8 | 8 | float16 | DDIM | 1 | Same as #1 |
| 5 | 8 | 8 | float16 | Euler | 1 | Same as #1 |
| 6 | 16 | 20 | float16 | DPM++ Karras | 1 | Frame 0 = input, frames 1-15 coherent moving scene, unrelated to the input's look |
| 7 | 16 | 12 | float16 | DPM++ | 1 | Out of memory in the attention layers |

Diagnostics that ruled things out:

- CPU against MPS, component by component: identical (see "What works").
- Plain Stable Diffusion image: correct, so base weights, text encoder and VAE
  are fine.
- Motion adapter loading info: no missing or mismatched weights.
- Three schedulers (#1, #4, #5): no difference.

Not tried: attention slicing (the first attempt used a call that does not exist
in this `diffusers` version; the retry was cut short), any size above 256,
a real photograph as input, the pipeline without the adapter LoRA, FreeNoise or
sliding windows for more than 16 frames, CPU offloading.

## Memory and time

Weights alone take 4.65 GB on the GPU in float16 (9.3 GB in float32). "Driver
peak" is everything Metal reserved for the process and is the number that
decides whether a run fits.

| Run | Generation time | Per step | MPS tensors peak | MPS driver peak | Lowest free RAM |
|-----|-----------------|----------|------------------|-----------------|-----------------|
| #1: 8 frames, 8 steps, float16 | 27 s | 3.4 s | 5.2 GB | 7.8 GB | 1.6 GB |
| #2: 8 frames, 8 steps, float32 | 270 s | 33.8 s | 10.3 GB | 13.3 GB | 0.8 GB |
| #6: 16 frames, 20 steps, float16 | 994 s | 49.7 s | 5.7 GB | 9.8 GB | 1.0 GB |

- Runs #3-#5 took 24-25 s each (3.0-3.1 s per step), driver 6.7-7.8 GB.
- Run #7 failed with: "MPS backend out of memory (MPS allocated: 5.55 GiB, other
  allocations: 10.47 GiB, max allowed: 18.13 GiB). Tried to allocate 2.56 GiB".
- Run #6's time is inflated: it started right after the float32 run, with system
  swap almost full, and other apps (browser, editor) were open throughout. A
  clean 16-frame timing has not been measured.
- Float32 is not an option on this machine.
- Loading the model takes about 10 s.

Raw logs for #1, #2 and #6 are JSON files next to the clips in
`outputs/generation/smoke/` (git-ignored, on the shared MacBook in
`project-friend`).

## Next steps

On the Mac:

1. Rerun 16 frames with `--attention-slicing` after closing other apps, and
   record a clean time and memory peak. This targets the layer that ran out of
   memory.
2. Separate the two causes in problem 1: 16 frames at 8 steps, and 8 frames at
   20 steps.
3. Use a real, openly licensed photograph of a player as input and see whether
   the clip keeps its appearance. If not, try a lower guidance scale, a prompt
   that describes the photo, or IP-Adapter for identity.
4. Go to 384 and then 512 pixels at 16 frames. If that does not fit: CPU
   offloading, VAE decoding in chunks, fewer steps.
5. For 60-100 frames, use AnimateDiff's sliding-window options (FreeNoise)
   rather than one long window.
6. Make the smoke test's checks stricter, for example compare later frames
   against frame 0, so a broken clip fails.

On Google Colab or Kaggle (free T4 GPU, 16 GB of dedicated video memory):

1. Add a `--device` option to `generation/smoke_test.py`; it is fixed to `mps`
   today. Nothing else in the pipeline is Mac-specific.
2. Notebook: clone the repo, `pip install -r generation/requirements.txt`, run
   `generation.download_weights`, then the smoke test with
   `--frames 16 --steps 25 --size 512`.
3. Use it for the heavy runs (512x512, long clips) and keep the Mac for small
   iterations. This was already planned for Turn 4.

Pose conditioning (OpenPose ControlNet driven by `pose/` output) is Milestone 3
and has not been started.
