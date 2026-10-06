"""Temporal smoothing of a pose sequence."""
from __future__ import annotations

import copy

import numpy as np

from .format import PoseSequence


def _moving_average(values: np.ndarray, detected: np.ndarray, window: int) -> np.ndarray:
    """Centered mean over `window` frames, using only detected frames."""
    half = window // 2
    out = values.copy()
    for t in np.flatnonzero(detected):
        lo, hi = max(0, t - half), min(len(values), t + half + 1)
        out[t] = values[lo:hi][detected[lo:hi]].mean(axis=0)
    return out


def smooth(seq: PoseSequence, window: int = 5) -> PoseSequence:
    """Return a copy of `seq` with joint positions averaged over `window` frames.

    Undetected frames stay NaN and are left out of their neighbours' averages,
    so no gaps are filled. `visibility` is unchanged.
    """
    if window < 1 or window % 2 == 0:
        raise ValueError(f"window must be a positive odd number, got {window}")
    meta = copy.deepcopy(seq.meta)
    meta.setdefault("processing", []).append({"step": "smooth", "method": "moving_average", "window": window})
    out = PoseSequence(
        keypoints=_moving_average(seq.keypoints, seq.detected, window),
        world=_moving_average(seq.world, seq.detected, window),
        visibility=seq.visibility.copy(),
        detected=seq.detected.copy(),
        frame_index=seq.frame_index.copy(),
        timestamps=seq.timestamps.copy(),
        meta=meta,
    )
    out.validate()
    return out
