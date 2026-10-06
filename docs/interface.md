# Pose-sequence interface (Part 1 -> Part 2)

`pose/` (Part 1) writes one pose-sequence file per action clip. `generation/`
(Part 2) reads it. This file is the only contract between the two parts.

- **Schema version:** `1.0`
- **Reference implementation:** `pose/format.py` (`PoseSequence.save` / `.load`)
- **Container:** a single compressed NumPy archive, `<name>.npz`
- **Default location:** `outputs/poses/<clip name>.npz` (git-ignored)

One file holds **one person** over **T consecutive frames** of one source video.

## Arrays

| Key | Shape | Dtype | Meaning |
|-----|-------|-------|---------|
| `keypoints` | (T, 33, 3) | float32 | `x`, `y` normalized to the source frame: `x = 0` left edge, `x = 1` right edge, `y = 0` top, `y = 1` bottom. `z` is relative depth on roughly the same scale as `x`, origin at the hip midpoint, negative = closer to the camera. |
| `world` | (T, 33, 3) | float32 | The same joints as estimated 3D positions in metres, origin at the hip midpoint, `y` pointing down. Independent of where the person is in the frame. |
| `visibility` | (T, 33) | float32 | Per-joint confidence in [0, 1] that the joint is visible. |
| `detected` | (T,) | bool | `False` when no person was found in that frame. |
| `frame_index` | (T,) | int32 | Index of each row's frame in the source video (0-based). |
| `timestamps` | (T,) | float32 | `frame_index / fps`, in seconds. |
| `meta` | () | str | JSON object, see below. |

Rules:

- In a frame where `detected` is `False`, `keypoints` and `world` are all `NaN`
  and `visibility` is all `0`. They are never zero-filled or interpolated
  silently; a step that fills gaps must record itself in `meta.processing`.
- `x` and `y` may fall slightly outside [0, 1] when a joint is off-frame.
- Rows are in time order and `frame_index` increases by 1 per row.
- Pixel coordinates: `x * meta.width`, `y * meta.height`.

## Metadata (`meta`)

| Key | Required | Meaning |
|-----|----------|---------|
| `schema_version` | yes | `"1.0"`. Readers must reject a different major version. |
| `fps` | yes | Frame rate of the source video. |
| `width`, `height` | yes | Source frame size in pixels. |
| `joint_names` | yes | The 33 joint names, in array order (list below). |
| `estimator` | yes | e.g. `"mediapipe-pose-landmarker-heavy"`. |
| `estimator_version` | no | Library version that produced the file. |
| `source_video` | no | File name of the source clip (no directory). |
| `action` | no | Label such as `cover_drive`, `fast_bowling`, `leg_spin`. |
| `placeholder` | no | `true` if the source is placeholder footage. |
| `processing` | no | Ordered list of steps applied after raw extraction (e.g. smoothing, normalization, trimming). Empty for raw output. |

Readers must ignore keys they do not know.

## Joints

MediaPipe Pose (BlazePose) order. "Left" and "right" are the player's own left
and right.

| # | Name | # | Name | # | Name |
|---|------|---|------|---|------|
| 0 | nose | 11 | left_shoulder | 22 | right_thumb |
| 1 | left_eye_inner | 12 | right_shoulder | 23 | left_hip |
| 2 | left_eye | 13 | left_elbow | 24 | right_hip |
| 3 | left_eye_outer | 14 | right_elbow | 25 | left_knee |
| 4 | right_eye_inner | 15 | left_wrist | 26 | right_knee |
| 5 | right_eye | 16 | right_wrist | 27 | left_ankle |
| 6 | right_eye_outer | 17 | left_pinky | 28 | right_ankle |
| 7 | left_ear | 18 | right_pinky | 29 | left_heel |
| 8 | right_ear | 19 | left_index | 30 | right_heel |
| 9 | mouth_left | 20 | right_index | 31 | left_foot_index |
| 10 | mouth_right | 21 | left_thumb | 32 | right_foot_index |

## Reading a file

With the reference reader (validates on load):

```python
from pose.format import PoseSequence

seq = PoseSequence.load("outputs/poses/clip.npz")
seq.keypoints   # (T, 33, 3)
seq.pixels()    # (T, 33, 2) in source pixels
seq.fps
```

With plain NumPy, so `generation/` does not have to install `pose/`'s dependencies:

```python
import json
import numpy as np

with np.load("outputs/poses/clip.npz", allow_pickle=False) as data:
    keypoints = data["keypoints"]
    detected = data["detected"]
    meta = json.loads(str(data["meta"]))
```

## Notes for Part 2

- Most pose-conditioned video models (ControlNet/OpenPose-style adapters,
  MagicAnimate-style DensePose) take **rendered control images**, not raw
  coordinates. This file is the source of truth; rendering it to 512x512
  skeleton frames in whatever layout the chosen model expects is a small step
  on top. The 33 joints are a superset of the COCO-17 / OpenPose-18 body
  joints except the neck, which is the midpoint of joints 11 and 12.
- The source clip's frame rate and length will usually not match the 60-100
  frames the generator wants. Resampling in time is not part of schema 1.0;
  a step that does it must update `fps`, `frame_index`, `timestamps` and add
  itself to `meta.processing`.
- Coordinates are relative to the full source frame, not cropped to the player.
  Cropping and scaling the player to fill a square frame is planned for Turn 3
  and will be recorded in `meta.processing`.

## Changing this format

Change `pose/format.py`, this document and the tests in the same commit. Adding
an optional `meta` key or a new array is a minor bump (`1.1`); changing the shape
or meaning of an existing array is a major bump (`2.0`).
