"""Draw a pose sequence's skeleton on its source video.

    python -m pose.overlay clip.mp4 outputs/poses/clip.npz --smooth 5 --still
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from .format import JOINT_NAMES, PoseSequence
from .smooth import smooth

_J = {name: i for i, name in enumerate(JOINT_NAMES)}

# Limbs as joint-name pairs. The face is left as joints only.
LIMBS = tuple((_J[a], _J[b]) for a, b in (
    ("left_shoulder", "right_shoulder"), ("left_hip", "right_hip"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_wrist", "left_index"), ("left_wrist", "left_pinky"), ("left_wrist", "left_thumb"),
    ("right_wrist", "right_index"), ("right_wrist", "right_pinky"), ("right_wrist", "right_thumb"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
    ("left_ankle", "left_heel"), ("left_heel", "left_foot_index"), ("left_ankle", "left_foot_index"),
    ("right_ankle", "right_heel"), ("right_heel", "right_foot_index"), ("right_ankle", "right_foot_index"),
))

# BGR. Player's left side orange, right side cyan, centre line white.
LEFT, RIGHT, CENTRE = (0, 140, 255), (255, 200, 0), (255, 255, 255)


def _colour(*joints: int) -> tuple:
    sides = {JOINT_NAMES[j].split("_")[0] for j in joints}
    if sides == {"left"}:
        return LEFT
    if sides == {"right"}:
        return RIGHT
    return CENTRE


def draw_skeleton(bgr: np.ndarray, pixels: np.ndarray, visibility: np.ndarray,
                  min_visibility: float = 0.3) -> np.ndarray:
    """Draw one frame's joints `(33, 2)` in pixels onto `bgr` in place."""
    thickness = max(2, round(min(bgr.shape[:2]) / 240))
    ok = (visibility >= min_visibility) & np.isfinite(pixels).all(axis=1)
    points = [(int(round(x)), int(round(y))) if good else None for (x, y), good in zip(pixels, ok)]
    for a, b in LIMBS:
        if points[a] and points[b]:
            cv2.line(bgr, points[a], points[b], _colour(a, b), thickness, cv2.LINE_AA)
    for j, point in enumerate(points):
        if point:
            cv2.circle(bgr, point, thickness + 1, _colour(j), -1, cv2.LINE_AA)
            cv2.circle(bgr, point, thickness + 1, (0, 0, 0), 1, cv2.LINE_AA)
    return bgr


def best_frame(seq: PoseSequence) -> int:
    """Row of the detected frame with the highest mean joint visibility."""
    if not seq.detected.any():
        raise ValueError("no detected frames in the pose sequence")
    return int(np.argmax(np.where(seq.detected, seq.visibility.mean(axis=1), -1.0)))


def player_box(seq: PoseSequence, margin: float = 0.5) -> tuple:
    """Square `(x0, y0, side)` in source pixels around the player over the whole of `seq`.

    Centred on the median joint position; the side is the largest per-frame
    extent (99th percentile) plus `margin` of padding on each side. Medians and
    percentiles keep a few frames where the estimator jumped to another person
    from stretching the box. The square is clamped to the frame.
    """
    pixels = seq.pixels()[seq.detected]
    if not len(pixels):
        raise ValueError("no detected frames in the pose sequence")
    width, height = seq.meta["width"], seq.meta["height"]
    lo, hi = pixels.min(axis=1), pixels.max(axis=1)
    extent = np.percentile((hi - lo).max(axis=1), 99)
    travel = np.percentile((lo + hi) / 2, [1, 99], axis=0)
    side = int(min(extent * (1 + 2 * margin) + (travel[1] - travel[0]).max(), width, height))
    cx, cy = np.median((lo + hi) / 2, axis=0)
    x0 = int(np.clip(cx - side / 2, 0, width - side))
    y0 = int(np.clip(cy - side / 2, 0, height - side))
    return x0, y0, side


def trim(seq: PoseSequence, start: float = 0.0, end: Optional[float] = None) -> PoseSequence:
    """The rows of `seq` with `start <= timestamp < end` (seconds in the source video)."""
    keep = seq.timestamps >= start
    if end is not None:
        keep &= seq.timestamps < end
    if not keep.any():
        raise ValueError("no frames of the pose sequence in the requested time range")
    return PoseSequence(seq.keypoints[keep], seq.world[keep], seq.visibility[keep], seq.detected[keep],
                        seq.frame_index[keep], seq.timestamps[keep], seq.meta)


def render_overlay(
    video_path: Union[str, Path],
    seq: PoseSequence,
    output: Union[str, Path],
    *,
    still: Optional[Union[str, Path]] = None,
    still_row: Optional[int] = None,
    crop_size: Optional[int] = None,
) -> Path:
    """Write the frames covered by `seq` with the skeleton drawn on them.

    If `still` is given, row `still_row` (default: `best_frame`) is also saved
    there as an image. If `crop_size` is given, the output is the `player_box`
    region scaled to `crop_size` x `crop_size`; the pose data is not changed.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if still is not None and still_row is None:
        still_row = best_frame(seq)
    pixels = seq.pixels()
    if crop_size:
        x0, y0, side = player_box(seq)
        pixels = (pixels - np.array([x0, y0], dtype=np.float32)) * (crop_size / side)
    rows = {int(f): i for i, f in enumerate(seq.frame_index)}

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open video: {video_path}")
    writer = None
    try:
        index = -1
        last = int(seq.frame_index[-1])
        while index < last:
            ok, bgr = cap.read()
            if not ok:
                break
            index += 1
            row = rows.get(index)
            if row is None:
                continue
            if crop_size:
                bgr = cv2.resize(bgr[y0:y0 + side, x0:x0 + side], (crop_size, crop_size),
                                 interpolation=cv2.INTER_CUBIC)
            if writer is None:
                height, width = bgr.shape[:2]
                writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"avc1"), seq.fps, (width, height))
                if not writer.isOpened():
                    raise RuntimeError(f"could not open video writer for {output}")
            if seq.detected[row]:
                draw_skeleton(bgr, pixels[row], seq.visibility[row])
            writer.write(bgr)
            if still is not None and row == still_row:
                Path(still).parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(still), bgr)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
    if writer is None:
        raise ValueError(f"no frames of {video_path} match the pose sequence")
    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("poses", type=Path, help="pose file written by pose.extract")
    parser.add_argument("-o", "--output", type=Path, help="default: outputs/overlay/<pose file name>.mp4")
    parser.add_argument("--smooth", type=int, default=0, metavar="WINDOW",
                        help="moving-average window in frames (odd); 0 draws the raw joints")
    parser.add_argument("--start", type=float, default=0.0, help="start time in seconds")
    parser.add_argument("--end", type=float, default=None, help="end time in seconds")
    parser.add_argument("--crop", type=int, default=0, metavar="SIZE",
                        help="crop to the player and scale to SIZE x SIZE pixels; 0 keeps the full frame")
    parser.add_argument("--still", action="store_true", help="also save one frame as a PNG next to the video")
    parser.add_argument("--still-frame", type=int, default=None,
                        help="source frame index for the still (default: highest mean visibility)")
    args = parser.parse_args(argv)

    seq = PoseSequence.load(args.poses)
    if args.smooth:
        seq = smooth(seq, args.smooth)
    seq = trim(seq, args.start, args.end)
    output = args.output or Path("outputs/overlay") / f"{args.poses.stem}.mp4"
    still = output.with_suffix(".png") if args.still else None
    still_row = None
    if args.still_frame is not None:
        matches = np.flatnonzero(seq.frame_index == args.still_frame)
        if not len(matches):
            parser.error(f"frame {args.still_frame} is not in {args.poses}")
        still_row = int(matches[0])
    render_overlay(args.video, seq, output, still=still, still_row=still_row,
                   crop_size=args.crop or None)
    print(f"{output}: {len(seq)} frames, skeleton drawn on {int(seq.detected.sum())}")
    if still:
        print(f"{still}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
