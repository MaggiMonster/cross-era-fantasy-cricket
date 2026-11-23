"""Tests for generation/memlog.py and the smoke test's helpers.

These need only psutil, numpy and Pillow, not torch or any weights. They are
skipped under pose/.venv, which has no psutil; run them with:

    generation/.venv/bin/python -m pytest tests/test_generation_memlog.py -q
"""

import json

import numpy as np
import pytest

pytest.importorskip("psutil")
pytest.importorskip("PIL")

from generation.config import ALL_MODELS, MODELS_DIR  # noqa: E402
from generation.memlog import MemoryLogger, snapshot  # noqa: E402
from generation.smoke_test import check_frames, load_image, placeholder_image  # noqa: E402


def test_snapshot_has_expected_fields():
    snap = snapshot()
    for key in ("rss_mb", "system_available_mb", "system_total_mb",
                "swap_used_mb", "mps_allocated_mb", "mps_driver_mb"):
        assert key in snap
        assert snap[key] >= 0
    assert snap["rss_mb"] > 0
    assert snap["system_total_mb"] >= snap["system_available_mb"]


def test_logger_records_checkpoints_and_peaks(tmp_path):
    with MemoryLogger(interval=0.01, verbose=False) as mem:
        block = np.ones((64, 2**20), dtype=np.uint8)  # 64 MB, touched
        mem.mark("allocated")
        del block

    labels = [c["label"] for c in mem.checkpoints]
    assert labels == ["start", "allocated", "end"]
    assert mem.peak["rss_mb"] >= mem.checkpoints[0]["rss_mb"]
    assert mem.min_system_available_mb < float("inf")

    path = mem.save(tmp_path / "log" / "run.json", extra={"settings": {"frames": 8}})
    data = json.loads(path.read_text())
    assert data["settings"] == {"frames": 8}
    assert set(data["memory"]["peak"]) == set(MemoryLogger.PEAK_KEYS)
    assert len(data["memory"]["checkpoints"]) == 3


def test_weights_go_to_an_ignored_folder():
    assert MODELS_DIR.name == "models"  # covered by `models/` in .gitignore
    for spec in ALL_MODELS:
        assert spec.local_dir.parent == MODELS_DIR
    assert len({spec.local_dir for spec in ALL_MODELS}) == len(ALL_MODELS)


def test_placeholder_image_size():
    img = placeholder_image(256)
    assert img.size == (256, 256)
    assert np.asarray(img).std() > 5


def test_load_image_centre_crops_to_square(tmp_path):
    from PIL import Image

    src = tmp_path / "wide.png"
    Image.new("RGB", (400, 200), (10, 20, 30)).save(src)
    assert load_image(src, 128).size == (128, 128)


def test_check_frames_accepts_moving_video():
    rng = np.random.default_rng(0)
    frames = rng.integers(0, 255, size=(4, 16, 16, 3), dtype=np.uint8)
    stats = check_frames(frames)
    assert stats["pixel_std"] > 2 and stats["mean_frame_diff"] > 0.05


def test_check_frames_rejects_blank_and_static():
    with pytest.raises(RuntimeError, match="blank"):
        check_frames(np.zeros((4, 16, 16, 3), dtype=np.uint8))
    rng = np.random.default_rng(0)
    still = np.repeat(rng.integers(0, 255, size=(1, 16, 16, 3), dtype=np.uint8), 4, axis=0)
    with pytest.raises(RuntimeError, match="does not move"):
        check_frames(still)
