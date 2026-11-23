"""The JavaScript sampler must match the Python networks. Needs Node.js."""
from __future__ import annotations

import json
import math
import shutil
import subprocess

import numpy as np
import pytest

from duel.batting import LENGTHS, LINES, PRESSURES, SHOTS
from duel.engine import Duel
from duel.export_web import WEB_NETWORKS, build_export
from duel.matchup import MATCHUPS, load_matchup
from duel.types import Delivery, Shot

REPLAY = WEB_NETWORKS.parents[2] / "test" / "replay.mjs"
DUELS_PER_CASE = 150
FREE_DUELS = 4000


def python_probabilities(matchup) -> list[float]:
    """Every table cell, in the order web/test/replay.mjs prints them."""
    rows: list[float] = []
    for i, pressure in enumerate(PRESSURES):
        rows += matchup.bowler.length_table[i].tolist()
        for k, length in enumerate(LENGTHS):
            for line in LINES:
                delivery = Delivery(matchup.bowler.bowl_type, length, line)
                rows += list(matchup.batter.shot_probs(delivery, pressure).values())
                for shot in SHOTS:
                    rows += list(matchup.outcome_probs(delivery, Shot(shot), pressure).values())
    return rows


def play_python(matchup, seed: int, shots: list[str] | None) -> dict:
    game = Duel(matchup, seed=seed)
    balls = []
    while not game.state.is_over:
        forced = Shot(next(s for s in SHOTS if s.value == shots[len(balls)])) if shots else None
        r = game.play(forced)
        balls.append([r.delivery.length.value, r.delivery.line.value, r.shot.shot_type.value, r.outcome.kind.value])
    return {"balls": balls, "runs": game.state.runs, "won": game.state.batter_won}


@pytest.fixture(scope="module")
def matchups():
    return {m: load_matchup(*m) for m in MATCHUPS}


@pytest.fixture(scope="module")
def replay(matchups, tmp_path_factory):
    node = shutil.which("node")
    assert node, "Node.js is required: brew install node"
    duels, expected = [], []
    for m, matchup in matchups.items():
        for seed in range(DUELS_PER_CASE):
            choice = np.random.default_rng(10_000 + seed)
            for shots in (None, [SHOTS[i].value for i in choice.integers(len(SHOTS), size=18)]):
                expected.append(play_python(matchup, seed, shots))
                # A generator with the same seed yields the uniforms Python's choice() consumed.
                uniforms = np.random.default_rng(seed).random(4 * 18).tolist()  # at most 4 draws per ball
                duels.append({"batter": m[0], "bowler": m[1], "uniforms": uniforms, "shots": shots})
    path = tmp_path_factory.mktemp("replay") / "fixture.json"
    path.write_text(json.dumps({"duels": duels, "free_duels": FREE_DUELS}))
    out = subprocess.run([node, str(REPLAY), str(WEB_NETWORKS), str(path)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout), expected


def test_committed_export_is_current():
    assert json.loads(WEB_NETWORKS.read_text()) == json.loads(json.dumps(build_export()))


def test_every_probability_matches(matchups, replay):
    result, _ = replay
    for m, matchup in matchups.items():
        py = np.array(python_probabilities(matchup))
        js = np.array(result["probabilities"][f"{m[0]}-{m[1]}"])
        assert py.shape == js.shape
        assert np.abs(py - js).max() < 1e-12


def test_same_random_numbers_give_identical_duels(replay):
    result, expected = replay
    assert len(result["duels"]) == len(expected) == 2 * 2 * DUELS_PER_CASE
    for js, py in zip(result["duels"], expected):
        assert js["balls"] == py["balls"]
        assert (js["runs"], js["won"]) == (py["runs"], py["won"])


def test_js_generator_gives_the_python_win_rate(matchups, replay):
    result, _ = replay
    for m, matchup in matchups.items():
        wins = sum(play_python(matchup, 500_000 + s, None)["won"] for s in range(FREE_DUELS))
        py, js = wins / FREE_DUELS, result["winRates"][f"{m[0]}-{m[1]}"]
        pooled = (py + js) / 2
        assert abs(py - js) < 4 * math.sqrt(2 * pooled * (1 - pooled) / FREE_DUELS)
