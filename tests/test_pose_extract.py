from pathlib import Path

import cv2
import numpy as np
import pytest

from pose.estimator import MODEL_DIR, FramePose
from pose.extract import extract_poses
from pose.format import NUM_JOINTS, PoseSequence

FPS = 20.0
SIZE = (64, 48)  # width, height
PLACEHOLDER_CLIP = Path(__file__).resolve().parents[1] / "data/placeholder/amar_kala_batting_2025.webm"


@pytest.fixture
def synthetic_video(tmp_path):
    """A 10-frame blank video. Synthetic placeholder, not cricket footage."""
    path = tmp_path / "synthetic.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, SIZE)
    assert writer.isOpened()
    for i in range(10):
        writer.write(np.full((SIZE[1], SIZE[0], 3), i * 20, dtype=np.uint8))
    writer.release()
    return path


class FakeEstimator:
    """Returns a constant pose, and no pose at all on the frames in `miss`."""

    name = "fake"
    version = "0"

    def __init__(self, miss=()):
        self.miss = set(miss)
        self.calls = []

    def __call__(self, rgb, timestamp_ms):
        index = len(self.calls)
        self.calls.append((rgb.shape, timestamp_ms))
        if index in self.miss:
            return None
        return FramePose(
            keypoints=np.full((NUM_JOINTS, 3), 0.5, dtype=np.float32),
            world=np.zeros((NUM_JOINTS, 3), dtype=np.float32),
            visibility=np.ones(NUM_JOINTS, dtype=np.float32),
        )


def test_extracts_one_pose_per_frame(synthetic_video):
    estimator = FakeEstimator()
    seq = extract_poses(synthetic_video, estimator, action="cover_drive", placeholder=True)

    assert len(seq) == 10
    assert seq.detected.all()
    assert seq.frame_index.tolist() == list(range(10))
    np.testing.assert_allclose(seq.timestamps, np.arange(10) / FPS, atol=1e-6)
    assert estimator.calls[0][0] == (SIZE[1], SIZE[0], 3)
    assert [ts for _, ts in estimator.calls] == [i * 50 for i in range(10)]
    assert seq.meta["fps"] == FPS
    assert (seq.meta["width"], seq.meta["height"]) == SIZE
    assert seq.meta["action"] == "cover_drive"
    assert seq.meta["placeholder"] is True
    assert seq.meta["estimator"] == "fake"


def test_missed_frames_are_nan_and_flagged(synthetic_video):
    seq = extract_poses(synthetic_video, FakeEstimator(miss={3, 4}))

    assert seq.detected.tolist() == [True] * 3 + [False] * 2 + [True] * 5
    assert np.isnan(seq.keypoints[3:5]).all()
    assert np.isnan(seq.world[3:5]).all()
    assert (seq.visibility[3:5] == 0).all()
    assert not np.isnan(seq.keypoints[seq.detected]).any()


def test_start_and_end_trim_the_clip(synthetic_video):
    seq = extract_poses(synthetic_video, FakeEstimator(), start=0.1, end=0.3)

    assert seq.frame_index.tolist() == [2, 3, 4, 5]
    assert seq.timestamps[0] == pytest.approx(0.1)


def test_result_survives_save_and_load(synthetic_video, tmp_path):
    seq = extract_poses(synthetic_video, FakeEstimator(miss={0}))
    loaded = PoseSequence.load(seq.save(tmp_path / "out.npz"))
    np.testing.assert_array_equal(loaded.detected, seq.detected)


def test_missing_video_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_poses(tmp_path / "nope.mp4", FakeEstimator())


def test_empty_time_range_raises(synthetic_video):
    with pytest.raises(ValueError, match="no frames"):
        extract_poses(synthetic_video, FakeEstimator(), start=99.0)


@pytest.mark.skipif(
    not PLACEHOLDER_CLIP.exists() or not (MODEL_DIR / "pose_landmarker_lite.task").exists(),
    reason="needs the placeholder clip and the lite pose model (see pose/README.md)",
)
def test_mediapipe_finds_a_person_in_the_placeholder_clip():
    from pose.estimator import MediaPipeEstimator

    estimator = MediaPipeEstimator(variant="lite")
    try:
        seq = extract_poses(PLACEHOLDER_CLIP, estimator, start=4.0, end=5.0, placeholder=True)
    finally:
        estimator.close()
    assert seq.detected.mean() > 0.5
    xy = seq.keypoints[seq.detected][..., :2]
    assert ((xy > -0.5) & (xy < 1.5)).all()
