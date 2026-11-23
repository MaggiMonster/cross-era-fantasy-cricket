"""Measured pace-vs-spin adjustment for the batsmen. Method in docs/assumptions.md.

Rebuild the counts from the repo root: python -m duel.pace_spin
"""
from __future__ import annotations

import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from duel.cricsheet import BALLS_CSV, BATTERS, PLAYERS
from duel.types import BowlType, OutcomeType

BOWLER_TYPES = Path(__file__).parent / "data" / "bowler_types.csv"
PACE_SPIN_COUNTS = Path(__file__).parent / "data" / "pace_spin_counts.json"

STYLES = ("pace", "finger_spin", "wrist_spin")
FORMATS = ("tests", "ipl")
# Weight of Tests against IPL, matching batting.TEST_WEIGHT.
TEST_WEIGHT = 0.5
# Pseudo-balls of the batter's all-spin rate added to their wrist-spin record.
WRIST_PRIOR_BALLS = 500
# Pseudo-events that pull a noisy estimate back towards no effect.
SHRINK_EVENTS = 20
# Largest multiplier either way on wicket or boundary odds.
MAX_EFFECT = 1.5
NOT_BOWLER_WICKETS = {"run out", "retired hurt", "retired out", "obstructing the field"}


def load_bowler_types(path: Path = BOWLER_TYPES) -> dict[str, str]:
    with open(path, newline="") as f:
        types = {row["bowler"]: row["style"] for row in csv.DictReader(f)}
    unknown = set(types.values()) - set(STYLES)
    if unknown:
        raise ValueError(f"unknown bowling styles: {unknown}")
    return types


def build_counts() -> dict:
    """Tally each batter's legal balls by format and labelled bowling style."""
    types = load_bowler_types()
    names = {PLAYERS[b]: b for b in BATTERS}
    tally = {
        b: {f: {s: defaultdict(int) for s in STYLES} for f in FORMATS} for b in BATTERS
    }
    total, labelled = defaultdict(int), defaultdict(int)
    with gzip.open(BALLS_CSV, "rt", newline="") as f:
        for row in csv.DictReader(f):
            batter = names.get(row["batter"])
            if batter is None or int(row["wide"]):
                continue
            total[batter] += 1
            style = types.get(row["bowler"])
            if style is None:
                continue
            labelled[batter] += 1
            cell = tally[batter][row["format"]][style]
            runs = int(row["batter_runs"])
            cell["balls"] += 1
            cell["runs"] += runs
            cell["boundaries"] += runs in (4, 6)
            cell["outs"] += bool(row["dismissal"]) and row["dismissal"] not in NOT_BOWLER_WICKETS
    return {
        "coverage": {b: round(labelled[b] / total[b], 4) for b in BATTERS},
        "players": {
            b: {f: {s: dict(tally[b][f][s]) for s in STYLES} for f in FORMATS} for b in BATTERS
        },
    }


def _rate(cell: dict, event: str) -> float:
    return (cell.get(event, 0) + 0.5) / (cell.get("balls", 0) + 1)


def _merge(*cells: dict) -> dict:
    keys = ("balls", "runs", "boundaries", "outs")
    return {k: sum(c.get(k, 0) for c in cells) for k in keys}


def _style_rates(side: dict, event: str) -> dict[BowlType, float]:
    """Rate against pace and against leg-spin, with wrist spin backed by all spin."""
    spin = _merge(side["finger_spin"], side["wrist_spin"])
    wrist = side["wrist_spin"]
    prior = _rate(spin, event)
    leg = (wrist.get(event, 0) + WRIST_PRIOR_BALLS * prior) / (wrist.get("balls", 0) + WRIST_PRIOR_BALLS)
    return {BowlType.PACE: _rate(side["pace"], event), BowlType.SPIN: leg}


def _log_gap(side: dict, event: str) -> float:
    """log(rate against spin / rate against pace), shrunk by how many events support it."""
    rates = _style_rates(side, event)
    events = side["pace"].get(event, 0) + side["wrist_spin"].get(event, 0) + side["finger_spin"].get(event, 0)
    return float(np.log(rates[BowlType.SPIN] / rates[BowlType.PACE]) * events / (events + SHRINK_EVENTS))


def player_effects(player: str, data: dict) -> dict[BowlType, dict[str, float]]:
    """Multipliers on wicket and boundary odds, relative to the two batsmen pooled."""
    effects = {BowlType.PACE: {}, BowlType.SPIN: {}}
    for event, label in (("outs", "wicket"), ("boundaries", "boundary")):
        gap = 0.0
        for fmt, weight in (("tests", TEST_WEIGHT), ("ipl", 1 - TEST_WEIGHT)):
            own = _log_gap(data["players"][player][fmt], event)
            pooled = np.mean([_log_gap(data["players"][b][fmt], event) for b in BATTERS])
            gap += weight * (own - pooled)
        limit = np.log(MAX_EFFECT)
        half = float(np.clip(gap / 2, -limit, limit))
        effects[BowlType.SPIN][label] = float(np.exp(half))
        effects[BowlType.PACE][label] = float(np.exp(-half))
    return effects


def outcome_multipliers(player: str, bowl_types: list[BowlType], outcomes: list[OutcomeType]) -> np.ndarray:
    """Array (BowlType, Outcome) of this player's multipliers on the outcome table."""
    data = json.loads(PACE_SPIN_COUNTS.read_text())
    effects = player_effects(player, data)
    table = np.ones((len(bowl_types), len(outcomes)))
    for b, bowl in enumerate(bowl_types):
        for o, outcome in enumerate(outcomes):
            if outcome.is_wicket and outcome is not OutcomeType.RUN_OUT:
                table[b, o] = effects[bowl]["wicket"]
            elif outcome in (OutcomeType.FOUR, OutcomeType.SIX):
                table[b, o] = effects[bowl]["boundary"]
    return table


if __name__ == "__main__":
    PACE_SPIN_COUNTS.write_text(json.dumps(build_counts(), indent=1) + "\n")
    print(f"wrote {PACE_SPIN_COUNTS}")
