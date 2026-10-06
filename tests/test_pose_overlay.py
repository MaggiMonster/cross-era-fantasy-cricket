import cv2
import numpy as np
import pytest

from pose.format import JOINT_NAMES, NUM_JOINTS, SCHEMA_VERSION, PoseSequence
from pose.overlay import best_frame, player_box, render_overlay, trim
from pose.smooth import smooth

FPS = 20.0
SIZE = (64, 48)  # width, height


def make_seq(keypoints, detected=None):
    t = len(keypoints)
    detected = np.ones(t, dtype=bool) if detected is None else np.asarray(detected, dtype=bool)
    keypoints = np.array(keypoints, dtype=np.float32)
    keypoints[~detected] = np.nan
    return PoseSequence(
        keypoints=keypoints,
        world=keypoints.copy(),
        visibility=np.where(detected[:, None], 0.9, 0.0).astype(np.float32) * np.ones((t, NUM_JOINTS), np.float32),
        detected=detected,
        frame_index=np.arange(t, dtype=np.int32),
        timestamps=(np.arange(t) / FPS).astype(np.float32),
        meta={"schema_version": SCHEMA_VERSION, "fps": FPS, "width": SIZE[0], "height": SIZE[1],
              "joint_names": list(JOINT_NAMES), "estimator": "fake", "processing": []},
    )


def test_smooth_reduces_jitter_and_keeps_the_trend():
    rng = np.random.default_rng(0)
    trend = np.linspace(0.2, 0.8, 40)[:, None, None] * np.ones((40, NUM_JOINTS, 3))
    seq = make_seq(trend + rng.normal(0, 0.02, trend.shape))
    out = smooth(seq, 5)
    assert np.abs(out.keypoints - trend).mean() < 0.6 * np.abs(seq.keypoints - trend).mean()
    assert out.meta["processing"] == [{"step": "smooth", "method": "moving_average", "window": 5}]
    assert seq.meta["processing"] == []


def test_smooth_does_not_fill_or_use_undetected_frames():
    keypoints = np.full((7, NUM_JOINTS, 3), 0.5)
    keypoints[4:] = 0.7
    detected = [True, True, True, False, True, True, True]
    out = smooth(make_seq(keypoints, detected), 3)
    assert np.isnan(out.keypoints[3]).all()
    assert np.array_equal(out.detected, detected)
    # Neighbours of the gap average only the real frames next to them.
    assert np.allclose(out.keypoints[2], 0.5)
    assert np.allclose(out.keypoints[4], 0.7)


def test_smooth_rejects_even_window():
    with pytest.raises(ValueError):
        smooth(make_seq(np.full((3, NUM_JOINTS, 3), 0.5)), 4)


def test_trim_keeps_the_time_range():
    seq = trim(make_seq(np.full((10, NUM_JOINTS, 3), 0.5)), 0.1, 0.3)
    assert list(seq.frame_index) == [2, 3, 4, 5]


def test_player_box_ignores_a_stray_frame_and_stays_in_frame():
    keypoints = np.full((200, NUM_JOINTS, 3), 0.5)
    keypoints[:, 0, :2] = 0.4
    keypoints[7, :, :2] = 0.95  # estimator jumped to someone else for one frame
    x0, y0, side = player_box(make_seq(keypoints))
    assert 0 <= x0 and x0 + side <= SIZE[0] and 0 <= y0 and y0 + side <= SIZE[1]
    assert x0 <= 0.4 * SIZE[0] and 0.5 * SIZE[0] <= x0 + side < 0.95 * SIZE[0]


def test_best_frame_is_a_detected_frame():
    seq = make_seq(np.full((4, NUM_JOINTS, 3), 0.5), [False, True, True, False])
    seq.visibility[2] = 1.0
    assert best_frame(seq) == 2


@pytest.mark.parametrize("crop_size", [None, 32])
def test_render_overlay_writes_video_and_still(tmp_path, crop_size):
    """Uses a blank synthetic video (placeholder, not cricket footage)."""
    video = tmp_path / "synthetic.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), FPS, SIZE)
    assert writer.isOpened()
    for _ in range(10):
        writer.write(np.zeros((SIZE[1], SIZE[0], 3), dtype=np.uint8))
    writer.release()

    keypoints = np.full((6, NUM_JOINTS, 3), 0.5)
    keypoints[:, ::2, :2] = 0.3
    seq = make_seq(keypoints, [True, True, False, True, True, True])
    out = render_overlay(video, seq, tmp_path / "out" / "overlay.mp4",
                         still=tmp_path / "out" / "still.png", crop_size=crop_size)

    cap = cv2.VideoCapture(str(out))
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 6
    cap.release()
    still = cv2.imread(str(tmp_path / "out" / "still.png"))
    assert still.shape[:2] == ((crop_size, crop_size) if crop_size else (SIZE[1], SIZE[0]))
    assert still.max() > 100  # something was drawn on the black frame
