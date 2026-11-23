import numpy as np
import pytest

from pose.format import JOINT_NAMES, NUM_JOINTS, SCHEMA_VERSION, PoseSequence


def make_sequence(frames=5, undetected=(2,)):
    rng = np.random.default_rng(0)
    keypoints = rng.random((frames, NUM_JOINTS, 3), dtype=np.float32)
    world = rng.random((frames, NUM_JOINTS, 3), dtype=np.float32)
    visibility = rng.random((frames, NUM_JOINTS), dtype=np.float32)
    detected = np.ones(frames, dtype=bool)
    for i in undetected:
        detected[i] = False
        keypoints[i] = np.nan
        world[i] = np.nan
        visibility[i] = 0.0
    frame_index = np.arange(frames, dtype=np.int32)
    return PoseSequence(
        keypoints=keypoints,
        world=world,
        visibility=visibility,
        detected=detected,
        frame_index=frame_index,
        timestamps=(frame_index / 25.0).astype(np.float32),
        meta={
            "schema_version": SCHEMA_VERSION,
            "fps": 25.0,
            "width": 640,
            "height": 480,
            "joint_names": list(JOINT_NAMES),
            "estimator": "fake",
        },
    )


def test_joint_names_match_joint_count():
    assert len(JOINT_NAMES) == NUM_JOINTS
    assert len(set(JOINT_NAMES)) == NUM_JOINTS


def test_save_load_round_trip(tmp_path):
    seq = make_sequence()
    path = seq.save(tmp_path / "poses" / "clip.npz")
    loaded = PoseSequence.load(path)

    assert len(loaded) == len(seq)
    np.testing.assert_array_equal(loaded.keypoints, seq.keypoints)
    np.testing.assert_array_equal(loaded.world, seq.world)
    np.testing.assert_array_equal(loaded.detected, seq.detected)
    np.testing.assert_array_equal(loaded.frame_index, seq.frame_index)
    assert loaded.meta == seq.meta
    assert loaded.fps == 25.0


def test_file_is_readable_with_plain_numpy(tmp_path):
    # Part 2 must be able to read the file without importing pose/.
    path = make_sequence().save(tmp_path / "clip.npz")
    with np.load(path, allow_pickle=False) as data:
        assert data["keypoints"].shape == (5, NUM_JOINTS, 3)
        assert data["keypoints"].dtype == np.float32
        assert data["detected"].dtype == np.bool_


def test_pixels_scales_by_frame_size():
    seq = make_sequence(undetected=())
    seq.keypoints[0, 0] = [0.5, 0.25, 0.0]
    np.testing.assert_allclose(seq.pixels()[0, 0], [320.0, 120.0])


def test_validate_rejects_wrong_shape():
    seq = make_sequence()
    seq.visibility = seq.visibility[:-1]
    with pytest.raises(ValueError, match="visibility"):
        seq.validate()


def test_validate_rejects_missing_meta():
    seq = make_sequence()
    del seq.meta["fps"]
    with pytest.raises(ValueError, match="fps"):
        seq.validate()


def test_validate_rejects_real_values_in_undetected_frame():
    seq = make_sequence()
    seq.keypoints[2] = 0.5
    with pytest.raises(ValueError, match="undetected"):
        seq.validate()


def test_load_rejects_unknown_major_version(tmp_path):
    seq = make_sequence()
    seq.meta["schema_version"] = "2.0"
    path = seq.save(tmp_path / "clip.npz")
    with pytest.raises(ValueError, match="schema_version"):
        PoseSequence.load(path)
