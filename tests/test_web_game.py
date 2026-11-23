"""Browser-game logic that runs under Node, and the validation helpers."""
from __future__ import annotations

import shutil
import subprocess

from duel.export_web import WEB_NETWORKS
from duel.validate import TOP_BOWLERS, simulate, top_bowlers

WEB = WEB_NETWORKS.parents[2]


def test_ball_physics():
    node = shutil.which("node")
    assert node, "Node.js is required: brew install node"
    tests = sorted(str(p) for p in (WEB / "test").glob("*.test.mjs"))
    out = subprocess.run([node, "--test", *tests], cwd=WEB, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:]


def test_simulation_is_reproducible():
    first, second = (simulate("kohli", "warne", duels=50, seed=4) for _ in range(2))
    assert first["win_rate"] == second["win_rate"]
    assert first["rates"] == second["rates"]


def test_top_bowlers_are_sorted():
    rows = top_bowlers("tendulkar")
    assert len(rows) == TOP_BOWLERS
    assert [r[1] for r in rows] == sorted((r[1] for r in rows), reverse=True)
