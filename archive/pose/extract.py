"""Extract a pose sequence from a video.

    python -m pose.extract clip.mp4 -o outputs/poses/clip.npz --action cover_drive
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Optional, Union

import cv2
import numpy as np

from .estimator import VARIANTS, FramePose, MediaPipeEstimator
from .format import JOINT_NAMES, NUM_JOINTS, SCHEMA_VERSION, PoseSequence

Estimator = Callable[[np.ndarray, int], Optional[FramePose]]


def extract_poses(
    video_path: Union[str, Path],
    estimator: Estimator,
    *,
    action: Optional[str] = None,
    start: float = 0.0,
    end: Optional[float] = None,
    placeholder: bool = False,
) -> PoseSequence:
    """Run `estimator` on every frame of `video_path` between `start` and `end` seconds."""
    video_path = Path(video_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open video: {video_path}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            raise ValueError(f"video reports no frame rate: {video_path}")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        keypoints, world, visibility, detected, frame_index = [], [], [], [], []
        nan_joints = np.full((NUM_JOINTS, 3), np.nan, dtype=np.float32)
        index = -1
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            index += 1
            t = index / fps
            if t < start:
                continue
            if end is not None and t >= end:
                break
            pose = estimator(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), int(round(t * 1000)))
            frame_index.append(index)
            detected.append(pose is not None)
            if pose is None:
                keypoints.append(nan_joints)
                world.append(nan_joints)
                visibility.append(np.zeros(NUM_JOINTS, dtype=np.float32))
            else:
                keypoints.append(pose.keypoints)
                world.append(pose.world)
                visibility.append(pose.visibility)
    finally:
        cap.release()

    if not frame_index:
        raise ValueError(f"no frames read from {video_path} in the requested time range")

    frame_index_arr = np.array(frame_index, dtype=np.int32)
    seq = PoseSequence(
        keypoints=np.stack(keypoints).astype(np.float32),
        world=np.stack(world).astype(np.float32),
        visibility=np.stack(visibility).astype(np.float32),
        detected=np.array(detected, dtype=np.bool_),
        frame_index=frame_index_arr,
        timestamps=(frame_index_arr / fps).astype(np.float32),
        meta={
            "schema_version": SCHEMA_VERSION,
            "fps": float(fps),
            "width": width,
            "height": height,
            "joint_names": list(JOINT_NAMES),
            "estimator": getattr(estimator, "name", type(estimator).__name__),
            "estimator_version": getattr(estimator, "version", None),
            "source_video": video_path.name,
            "action": action,
            "placeholder": placeholder,
            "processing": [],
        },
    )
    seq.validate()
    return seq


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="default: outputs/poses/<video name>.npz")
    parser.add_argument("--action", help="label for the action, e.g. cover_drive, fast_bowling, leg_spin")
    parser.add_argument("--start", type=float, default=0.0, help="start time in seconds")
    parser.add_argument("--end", type=float, default=None, help="end time in seconds")
    parser.add_argument("--model", choices=VARIANTS, default="heavy")
    parser.add_argument("--placeholder", action="store_true",
                        help="mark the source clip as placeholder footage (CLAUDE.md rule 4)")
    args = parser.parse_args(argv)

    output = args.output or Path("outputs/poses") / f"{args.video.stem}.npz"
    estimator = MediaPipeEstimator(variant=args.model)
    try:
        seq = extract_poses(args.video, estimator, action=args.action, start=args.start,
                            end=args.end, placeholder=args.placeholder)
    finally:
        estimator.close()
    seq.save(output)

    n = len(seq)
    hits = int(seq.detected.sum())
    print(f"{output}: {n} frames at {seq.fps:.2f} fps, person detected in {hits}/{n} "
          f"({100 * hits / n:.0f}%)")
    if hits:
        print(f"mean joint visibility on detected frames: {seq.visibility[seq.detected].mean():.2f}")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
