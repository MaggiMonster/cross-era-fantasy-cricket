"""Pose estimator backends.

An estimator takes one RGB frame plus its timestamp and returns a `FramePose`
(or None when no person is found). `MediaPipeEstimator` is the real backend;
tests substitute a fake so they need neither the model file nor a real video.
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_{variant}/float16/latest/pose_landmarker_{variant}.task"
)
VARIANTS = ("lite", "full", "heavy")


@dataclass
class FramePose:
    keypoints: np.ndarray   # (33, 3) normalized image coords
    world: np.ndarray       # (33, 3) metres, hip-centred
    visibility: np.ndarray  # (33,)


def ensure_model(variant: str = "heavy") -> Path:
    """Return the local path of the pose model, downloading it on first use."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    path = MODEL_DIR / f"pose_landmarker_{variant}.task"
    if not path.exists():
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(MODEL_URL.format(variant=variant), tmp)
        tmp.rename(path)
    return path


class MediaPipeEstimator:
    """MediaPipe Pose Landmarker (BlazePose GHUM, 33 joints) in video mode."""

    def __init__(self, variant: str = "heavy", min_confidence: float = 0.5):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._mp = mp
        self.name = f"mediapipe-pose-landmarker-{variant}"
        self.version = mp.__version__
        options = vision.PoseLandmarkerOptions(
            # CPU delegate: the Metal GPU delegate aborts the process when no GPU
            # service is available (headless shells, sandboxes), and CPU is fast enough.
            base_options=mp_python.BaseOptions(
                model_asset_path=str(ensure_model(variant)),
                delegate=mp_python.BaseOptions.Delegate.CPU,
            ),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_confidence,
            min_pose_presence_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)

    def __call__(self, rgb: np.ndarray, timestamp_ms: int) -> Optional[FramePose]:
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.pose_landmarks:
            return None
        image_lms = result.pose_landmarks[0]
        world_lms = result.pose_world_landmarks[0]
        return FramePose(
            keypoints=np.array([[lm.x, lm.y, lm.z] for lm in image_lms], dtype=np.float32),
            world=np.array([[lm.x, lm.y, lm.z] for lm in world_lms], dtype=np.float32),
            visibility=np.array([lm.visibility or 0.0 for lm in image_lms], dtype=np.float32),
        )

    def close(self) -> None:
        self._landmarker.close()
