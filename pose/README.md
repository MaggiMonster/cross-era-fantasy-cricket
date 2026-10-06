# pose/ - motion extraction (Part 1)

Reads a video, runs a pose estimator on every frame and writes a pose-sequence
file in the format defined in [`docs/interface.md`](../docs/interface.md).

## Setup

From the repo root:

```sh
python3 -m venv pose/.venv
pose/.venv/bin/pip install -r pose/requirements.txt
```

The pose model (about 30 MB) is downloaded to `pose/models/` on first use.

## Usage

```sh
pose/.venv/bin/python -m pose.extract data/placeholder/amar_kala_batting_2025.webm \
    --action cover_drive --start 0 --end 8 --placeholder
```

| Option | Meaning |
|--------|---------|
| `-o PATH` | Output file. Default `outputs/poses/<video name>.npz`. |
| `--action LABEL` | Stored in the file's metadata. |
| `--start S`, `--end S` | Only process this time range, in seconds. |
| `--model lite\|full\|heavy` | Model size. Default `heavy` (most accurate). |
| `--placeholder` | Mark the source as placeholder footage. |

It prints how many frames had a person detected and exits with status 1 if
none did.

From Python:

```python
from pose.estimator import MediaPipeEstimator
from pose.extract import extract_poses

estimator = MediaPipeEstimator()
seq = extract_poses("clip.mp4", estimator, action="fast_bowling")
seq.save("outputs/poses/clip.npz")
```

## Skeleton overlay

Draws the joints and limbs of a pose file on its source video, to check the
extraction by eye. Player's left side is orange, right side cyan.

```sh
pose/.venv/bin/python -m pose.overlay data/placeholder/amar_kala_batting_2025.webm \
    outputs/poses/amar_kala_batting_2025.npz \
    --smooth 5 --start 2.4 --end 4.4 --crop 720 --still --still-frame 104 \
    -o outputs/overlay/amar_kala_batting_2025_skeleton_crop.mp4
```

| Option | Meaning |
|--------|---------|
| `-o PATH` | Output video (H.264 `.mp4`). Default `outputs/overlay/<pose file name>.mp4`. |
| `--smooth WINDOW` | Smooth the joints first (see below). `0`, the default, draws the raw joints. |
| `--start S`, `--end S` | Only this time range of the source video, in seconds. |
| `--crop SIZE` | Crop to the player and scale to SIZE x SIZE pixels. The crop is one fixed square for the whole range, so keep the range inside one camera shot. |
| `--still` | Also save one frame as a PNG next to the video. |
| `--still-frame N` | Source frame number for the still. Default: the frame with the highest mean joint visibility. |

The crop only affects the picture. Pose files stay in full-frame coordinates.

## Smoothing

`pose.smooth.smooth(seq, window=5)` returns a copy with every joint position
replaced by its mean over `window` frames (centered moving average), and records
the step in `meta.processing`. Undetected frames stay `NaN` and are not used in
their neighbours' averages, so gaps are never filled.

On the placeholder clip a 5-frame window cuts frame-to-frame jitter (mean second
difference of joint positions) from 6.0 to 1.4 pixels. It is a plain average: it
also rounds off fast movements such as the bat swing, and it averages straight
across camera cuts. A filter that adapts to speed (for example One Euro) is the
likely replacement.

## Files

- `format.py` - `PoseSequence`: the file format, validation, save/load.
- `estimator.py` - `MediaPipeEstimator` and the model download.
- `extract.py` - video loop and command-line entry point.
- `smooth.py` - moving-average smoothing.
- `overlay.py` - skeleton-overlay video and still image.

## Why MediaPipe

The estimator has to run on an Apple Silicon Mac with no CUDA, alongside a
diffusion model that will want most of the 16 GB.

| Option | Verdict |
|--------|---------|
| **MediaPipe Pose Landmarker** (BlazePose GHUM) | **Chosen.** A pip install with native arm64 wheels, no PyTorch, about 30 MB model, runs on CPU faster than real time for our clip sizes. 33 joints including hands and feet, which matter for grip and the front-foot landing, plus 3D world coordinates. Apache 2.0. |
| OpenPose | Standard skeleton for ControlNet adapters, but the original build is CUDA/Caffe and painful on macOS. We can render OpenPose-style images from MediaPipe joints instead. |
| MMPose / RTMPose, ViTPose | More accurate on hard poses, but pull in PyTorch plus the mmcv stack, whose Apple Silicon support is patchy. Worth revisiting only if MediaPipe accuracy turns out to be the bottleneck. |
| YOLO-pose (Ultralytics) | Easy install and multi-person, but only 17 joints (no hands or feet) and AGPL licence. |
| DensePose / SMPL meshes | What MagicAnimate expects; Detectron2 on macOS is a heavy dependency. Deferred until Part 2 has chosen a model that needs it. |

Known limits of this choice:

- It tracks **one** person. In a wide shot with several players it picks the
  most prominent one, which may not be the player we want. Cropping to the
  player before extraction is the fix (planned for Turn 3).
- Small or motion-blurred players are missed in some frames. Those frames are
  stored as `NaN` with `detected = False`, never guessed.

### Version pin

`requirements.txt` pins `mediapipe==0.10.21`. The newest release at the time of
writing (1.0.1) aborts on this Mac when the pose graph opens ("Check failed:
service_ Service is unavailable" in the Metal helper), even with the CPU
delegate selected. 0.10.21 runs correctly on CPU. It needs `numpy<2`.

## Measured on the placeholder clip

MacBook Air M4, CPU, `heavy` model, first 8 s of the placeholder clip
(720x1280, 200 frames): about 20 s wall time including model load, person
detected in 154/200 frames (77%), mean joint visibility 0.79. The misses are the
first two seconds, where the batter is small and still. This clip is a distant
amateur shot; closer footage should do considerably better.

Seen in the overlay of those 8 s: the clip has camera cuts at frames 110 and
165; the one detection before frame 48 is on the non-striker, not the batter;
and in frames 48-58 the skeleton is stretched between the batter and the
wicketkeeper behind him. From frame 60 on it follows the batter, who is only
about 120 pixels tall, so hands and feet are approximate.

## Tests

```sh
pose/.venv/bin/python -m pytest tests -q
```

Most tests use a synthetic blank video and a fake estimator, so they need no
model or footage. One test runs the real `lite` model on the placeholder clip
and is skipped when either is missing (see [`data/README.md`](../data/README.md);
fetch the model with
`pose/.venv/bin/python -c "from pose.estimator import ensure_model; ensure_model('lite')"`).
