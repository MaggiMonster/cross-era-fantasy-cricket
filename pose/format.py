"""Pose-sequence file format shared by Part 1 (pose/) and Part 2 (generation/).

The format is specified in docs/interface.md. This module is the reference
reader/writer: anything that produces or consumes a pose file should go
through `PoseSequence.save` / `PoseSequence.load` so validation stays in one place.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Union

import numpy as np

SCHEMA_VERSION = "1.0"
NUM_JOINTS = 33

# MediaPipe Pose (BlazePose) landmark order. Index in this tuple == joint index
# on axis 1 of every per-joint array.
JOINT_NAMES = (
    "nose",
    "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
)

REQUIRED_META = ("schema_version", "fps", "width", "height", "joint_names", "estimator")


@dataclass
class PoseSequence:
    """One person's joints over T frames. See docs/interface.md for semantics."""

    keypoints: np.ndarray      # (T, 33, 3) float32  x, y normalized to [0, 1]; z relative depth
    world: np.ndarray          # (T, 33, 3) float32  metres, origin at hip midpoint
    visibility: np.ndarray     # (T, 33)    float32  confidence in [0, 1]
    detected: np.ndarray       # (T,)       bool     False => that frame's rows are NaN
    frame_index: np.ndarray    # (T,)       int32    index of the frame in the source video
    timestamps: np.ndarray     # (T,)       float32  seconds from the start of the source video
    meta: Dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return int(self.keypoints.shape[0])

    @property
    def fps(self) -> float:
        return float(self.meta["fps"])

    def pixels(self) -> np.ndarray:
        """(T, 33, 2) joint positions in source-video pixels."""
        return self.keypoints[..., :2] * np.array(
            [self.meta["width"], self.meta["height"]], dtype=np.float32
        )

    def validate(self) -> None:
        t = len(self)
        expected = {
            "keypoints": (t, NUM_JOINTS, 3),
            "world": (t, NUM_JOINTS, 3),
            "visibility": (t, NUM_JOINTS),
            "detected": (t,),
            "frame_index": (t,),
            "timestamps": (t,),
        }
        for name, shape in expected.items():
            actual = getattr(self, name).shape
            if actual != shape:
                raise ValueError(f"{name} has shape {actual}, expected {shape}")
        missing = [k for k in REQUIRED_META if k not in self.meta]
        if missing:
            raise ValueError(f"meta is missing required keys: {missing}")
        if list(self.meta["joint_names"]) != list(JOINT_NAMES):
            raise ValueError("meta.joint_names does not match the schema joint order")
        # Undetected frames must be NaN so consumers cannot mistake them for real poses.
        if np.isnan(self.keypoints[self.detected]).any():
            raise ValueError("NaN keypoints in a frame marked detected")
        if not np.isnan(self.keypoints[~self.detected]).all():
            raise ValueError("non-NaN keypoints in a frame marked undetected")

    def save(self, path: Union[str, Path]) -> Path:
        self.validate()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # np.savez appends ".npz" unless the name already ends with it.
        with open(path, "wb") as f:
            np.savez_compressed(
                f,
                keypoints=self.keypoints.astype(np.float32),
                world=self.world.astype(np.float32),
                visibility=self.visibility.astype(np.float32),
                detected=self.detected.astype(np.bool_),
                frame_index=self.frame_index.astype(np.int32),
                timestamps=self.timestamps.astype(np.float32),
                meta=np.array(json.dumps(self.meta)),
            )
        return path

    @classmethod
    def load(cls, path: Union[str, Path]) -> "PoseSequence":
        with np.load(Path(path), allow_pickle=False) as data:
            seq = cls(
                keypoints=data["keypoints"],
                world=data["world"],
                visibility=data["visibility"],
                detected=data["detected"],
                frame_index=data["frame_index"],
                timestamps=data["timestamps"],
                meta=json.loads(str(data["meta"])),
            )
        major = str(seq.meta.get("schema_version", "")).split(".")[0]
        if major != SCHEMA_VERSION.split(".")[0]:
            raise ValueError(
                f"unsupported pose schema_version {seq.meta.get('schema_version')!r}, "
                f"this reader handles {SCHEMA_VERSION}"
            )
        seq.validate()
        return seq
