"""Batting Bayesian networks. Structure in docs/interface.md, priors in docs/assumptions.md."""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
from pgmpy.factors.discrete import TabularCPD
from pgmpy.models import DiscreteBayesianNetwork

from duel.career import load_career_stats
from duel.cricsheet import BATTERS, BATTING_COUNTS
from duel.pace_spin import outcome_multipliers
from duel.types import (
    BowlType,
    Delivery,
    Length,
    Line,
    MatchState,
    OutcomeType,
    Pressure,
    Shot,
    ShotType,
)

BOWL_TYPES = list(BowlType)
LENGTHS = list(Length)
LINES = list(Line)
PRESSURES = list(Pressure)
SHOTS = list(ShotType)
OUTCOMES = list(OutcomeType)
WICKET_MASK = np.array([o.is_wicket for o in OUTCOMES])

# Pseudo-balls of the player's overall IPL rates added to each pressure group.
SMOOTHING_BALLS = 100
# Weight of Tests against IPL for relative dismissal risk and dismissal mix.
TEST_WEIGHT = 0.5

# Reference delivery mix, used only to calibrate Outcome to the observed rates.
REFERENCE_BOWL = np.array([0.5, 0.5])
REFERENCE_LENGTH = np.array([[0.10, 0.25, 0.40, 0.20, 0.05], [0.03, 0.35, 0.45, 0.15, 0.02]])
REFERENCE_LINE = np.array([0.40, 0.45, 0.15])

# P(shot) weights before adjustment. Columns follow ShotType.
SHOT_BY_LENGTH = {
    Length.YORKER: [0.01, 0.50, 0.30, 0.12, 0.00, 0.00, 0.01, 0.06],
    Length.FULL: [0.05, 0.20, 0.20, 0.38, 0.01, 0.01, 0.05, 0.10],
    Length.GOOD: [0.14, 0.34, 0.24, 0.12, 0.07, 0.03, 0.03, 0.03],
    Length.SHORT: [0.08, 0.14, 0.18, 0.02, 0.26, 0.26, 0.02, 0.04],
    Length.BOUNCER: [0.30, 0.12, 0.08, 0.00, 0.08, 0.37, 0.00, 0.05],
}
SHOT_BY_LINE = {
    Line.OUTSIDE_OFF: [2.0, 0.8, 0.5, 1.3, 2.0, 0.7, 0.7, 1.0],
    Line.STUMPS: [0.1, 1.3, 1.0, 1.1, 0.4, 1.0, 1.0, 1.0],
    Line.LEG: [0.5, 0.8, 2.2, 0.4, 0.1, 1.5, 1.6, 1.0],
}
SHOT_BY_BOWL = {
    BowlType.PACE: [1.2, 1.0, 1.0, 1.0, 1.0, 1.2, 0.05, 0.8],
    BowlType.SPIN: [0.5, 1.0, 1.1, 1.0, 0.9, 0.7, 2.5, 1.2],
}
SHOT_ATTACK = np.array([-1.0, -0.7, 0.0, 0.4, 0.4, 0.5, 0.3, 1.2])
PRESSURE_TILT = {Pressure.LOW: -0.4, Pressure.MEDIUM: 0.0, Pressure.HIGH: 0.6}

# Outcome multipliers. Columns: dot, 1/2/3, 4, 6, bowled, lbw, caught, stumped, run out.
SHOT_EFFECT = {
    ShotType.LEAVE: [4.0, 0.01, 0.01, 0.001, 0.4, 0.6, 0.02, 0.02, 0.001],
    ShotType.DEFEND: [2.5, 0.3, 0.05, 0.005, 0.5, 0.7, 0.4, 0.15, 0.05],
    ShotType.WORK: [0.9, 1.8, 0.5, 0.1, 0.6, 1.3, 0.7, 0.4, 1.5],
    ShotType.DRIVE: [0.7, 1.0, 1.7, 0.6, 1.4, 0.8, 1.3, 0.8, 1.0],
    ShotType.CUT: [0.7, 1.0, 1.7, 0.4, 0.8, 0.2, 1.4, 0.5, 0.8],
    ShotType.PULL: [0.7, 0.9, 1.7, 1.6, 0.8, 0.8, 1.6, 0.2, 0.7],
    ShotType.SWEEP: [0.8, 1.1, 1.5, 0.7, 0.9, 1.8, 1.2, 0.8, 0.7],
    ShotType.LOFT: [0.6, 0.6, 1.5, 4.0, 1.4, 0.6, 2.6, 2.2, 0.5],
}
LENGTH_EFFECT = {
    Length.YORKER: [1.4, 0.7, 0.5, 0.3, 2.5, 2.0, 0.6, 0.3, 1.0],
    Length.FULL: [1.0, 1.0, 1.2, 1.1, 1.2, 1.2, 0.9, 0.9, 1.0],
    Length.GOOD: [1.1, 0.9, 0.8, 0.7, 1.0, 1.0, 1.0, 1.0, 1.0],
    Length.SHORT: [0.9, 1.1, 1.2, 1.2, 0.6, 0.5, 1.2, 0.7, 1.0],
    Length.BOUNCER: [1.3, 0.6, 0.9, 1.3, 0.2, 0.1, 1.4, 0.1, 0.7],
}
BOWL_EFFECT = {
    BowlType.PACE: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 0.1, 1.0],
    BowlType.SPIN: [1.0, 1.1, 0.9, 1.0, 1.0, 1.0, 0.9, 2.5, 1.0],
}
EFFECT_COLUMN = np.array([0, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8])  # OutcomeType -> column


def _logit(p: float) -> float:
    return float(np.log(p / (1 - p)))


def _expit(x: float) -> float:
    return float(1 / (1 + np.exp(-x)))


def _vector(tally: dict) -> np.ndarray:
    return np.array([tally.get(o.value, 0) for o in OUTCOMES], dtype=float)


def _hazard(v: np.ndarray) -> float:
    return float(v[WICKET_MASK].sum() / v.sum())


def _boundary_rate(v: np.ndarray) -> float:
    return float((v[OUTCOMES.index(OutcomeType.FOUR)] + v[OUTCOMES.index(OutcomeType.SIX)]) / v.sum())


def _test_hazard(player: str, counts: dict, career: dict) -> float:
    """Cricsheet's Test hazard, corrected to the player's full-career average."""
    v = _vector(counts[player]["tests"]["all"])
    runs = sum(o.runs * n for o, n in zip(OUTCOMES, v))
    window_average = runs / v[WICKET_MASK].sum()
    return _hazard(v) * window_average / career[player, "tests", "average"]


def observed_rates(player: str, counts: dict, career: dict) -> dict[Pressure, np.ndarray]:
    """P(Outcome | Pressure) from IPL chases, with the Tests + IPL skill blend."""
    ipl = _vector(counts[player]["ipl"]["all"])
    tests = _vector(counts[player]["tests"]["all"])
    pooled_ipl = sum(_vector(counts[b]["ipl"]["all"]) for b in BATTERS)
    pooled_test = sum(_vector(counts[b]["tests"]["all"]) for b in BATTERS)
    relative_test = _logit(_test_hazard(player, counts, career)) - _logit(_hazard(pooled_test))
    relative_ipl = _logit(_hazard(ipl)) - _logit(_hazard(pooled_ipl))
    shift = TEST_WEIGHT * (relative_test - relative_ipl)

    mix = TEST_WEIGHT * tests[WICKET_MASK] / tests[WICKET_MASK].sum()
    mix = mix + (1 - TEST_WEIGHT) * ipl[WICKET_MASK] / ipl[WICKET_MASK].sum()
    mix = (mix + 1e-3) / (mix + 1e-3).sum()

    rates = {}
    for pressure in PRESSURES:
        group = _vector(counts[player]["ipl"].get(pressure.value, {}))
        smoothed = (group + SMOOTHING_BALLS * ipl / ipl.sum() + 0.5) / (
            group.sum() + SMOOTHING_BALLS + 0.5 * len(OUTCOMES)
        )
        hazard = _expit(_logit(_hazard(smoothed)) + shift)
        p = smoothed.copy()
        p[~WICKET_MASK] *= (1 - hazard) / p[~WICKET_MASK].sum()
        p[WICKET_MASK] = hazard * mix
        rates[pressure] = p
    return rates


def _aggression(player: str, counts: dict) -> float:
    ipl = _vector(counts[player]["ipl"]["all"])
    pooled = sum(_vector(counts[b]["ipl"]["all"]) for b in BATTERS)
    return float(np.log(_boundary_rate(ipl) / _boundary_rate(pooled)))


def _shot_table(aggression: float) -> np.ndarray:
    """P(Shot | Pressure, BowlType, Length, Line), axes in that order plus Shot last."""
    table = np.zeros((len(PRESSURES), len(BOWL_TYPES), len(LENGTHS), len(LINES), len(SHOTS)))
    for i, pressure in enumerate(PRESSURES):
        tilt = np.exp(SHOT_ATTACK * (PRESSURE_TILT[pressure] + aggression))
        for j, bowl in enumerate(BOWL_TYPES):
            for k, length in enumerate(LENGTHS):
                for m, line in enumerate(LINES):
                    w = (
                        np.array(SHOT_BY_LENGTH[length])
                        * np.array(SHOT_BY_LINE[line])
                        * np.array(SHOT_BY_BOWL[bowl])
                        * tilt
                        + 1e-4
                    )
                    table[i, j, k, m] = w / w.sum()
    return table


def _outcome_table(
    shot_table: np.ndarray,
    rates: dict[Pressure, np.ndarray],
    bowl_multipliers: np.ndarray | None = None,
) -> np.ndarray:
    """P(Outcome | Pressure, Shot, BowlType, Length), calibrated to the observed rates.

    `bowl_multipliers` (BowlType, Outcome) is a batter's own pace-vs-spin effect. The
    population baseline leaves it out, so log5 keeps it in a matchup.
    """
    effect = np.ones((len(SHOTS), len(BOWL_TYPES), len(LENGTHS), len(OUTCOMES)))
    for s, shot in enumerate(SHOTS):
        for b, bowl in enumerate(BOWL_TYPES):
            for l, length in enumerate(LENGTHS):
                effect[s, b, l] = (
                    np.array(SHOT_EFFECT[shot])
                    * np.array(BOWL_EFFECT[bowl])
                    * np.array(LENGTH_EFFECT[length])
                )[EFFECT_COLUMN]
                if bowl_multipliers is not None:
                    effect[s, b, l] *= bowl_multipliers[b]

    table = np.zeros((len(PRESSURES), *effect.shape))
    for i, pressure in enumerate(PRESSURES):
        # Joint P(Shot, BowlType, Length) under the reference delivery mix.
        by_line = (shot_table[i] * REFERENCE_LINE[None, None, :, None]).sum(axis=2)
        joint = np.einsum("b,bl,bls->sbl", REFERENCE_BOWL, REFERENCE_LENGTH, by_line)
        target = rates[pressure]
        scale = target.copy()
        for _ in range(500):
            cell = effect * scale
            cell /= cell.sum(axis=-1, keepdims=True)
            marginal = np.einsum("sbl,sblo->o", joint, cell)
            scale *= target / marginal
            if np.abs(marginal - target).max() < 1e-9:
                break
        table[i] = cell
    return table


@dataclass
class BattingNetwork:
    player: str
    model: DiscreteBayesianNetwork
    shot_table: np.ndarray
    outcome_table: np.ndarray

    def shot_probs(self, delivery: Delivery, pressure: Pressure) -> dict[ShotType, float]:
        p = self.shot_table[
            PRESSURES.index(pressure),
            BOWL_TYPES.index(delivery.bowl_type),
            LENGTHS.index(delivery.length),
            LINES.index(delivery.line),
        ]
        return dict(zip(SHOTS, p.tolist()))

    def outcome_probs(
        self, delivery: Delivery, shot: Shot, pressure: Pressure
    ) -> dict[OutcomeType, float]:
        p = self.outcome_table[
            PRESSURES.index(pressure),
            SHOTS.index(shot.shot_type),
            BOWL_TYPES.index(delivery.bowl_type),
            LENGTHS.index(delivery.length),
        ]
        return dict(zip(OUTCOMES, p.tolist()))

    def sample_shot(self, delivery: Delivery, state: MatchState, rng: np.random.Generator) -> Shot:
        probs = self.shot_probs(delivery, state.pressure)
        return Shot(SHOTS[rng.choice(len(SHOTS), p=list(probs.values()))])


def _build_model(shot_table: np.ndarray, outcome_table: np.ndarray) -> DiscreteBayesianNetwork:
    names = {
        "Pressure": [p.value for p in PRESSURES],
        "BowlType": [b.value for b in BOWL_TYPES],
        "Length": [l.value for l in LENGTHS],
        "Line": [l.value for l in LINES],
        "Shot": [s.value for s in SHOTS],
        "Outcome": [o.value for o in OUTCOMES],
    }
    model = DiscreteBayesianNetwork(
        [
            ("Pressure", "Shot"), ("BowlType", "Shot"), ("Length", "Shot"), ("Line", "Shot"),
            ("BowlType", "Length"),
            ("Pressure", "Outcome"), ("Shot", "Outcome"), ("BowlType", "Outcome"), ("Length", "Outcome"),
        ]
    )

    def conditional(var, table, parents):
        return TabularCPD(
            var,
            len(names[var]),
            np.moveaxis(table, -1, 0).reshape(len(names[var]), -1),
            evidence=parents,
            evidence_card=[len(names[p]) for p in parents],
            state_names={v: names[v] for v in [var, *parents]},
        )

    uniform = np.full((len(PRESSURES), 1), 1 / len(PRESSURES))
    model.add_cpds(
        TabularCPD("Pressure", len(PRESSURES), uniform, state_names={"Pressure": names["Pressure"]}),
        TabularCPD("BowlType", 2, REFERENCE_BOWL[:, None], state_names={"BowlType": names["BowlType"]}),
        conditional("Length", REFERENCE_LENGTH, ["BowlType"]),
        TabularCPD("Line", len(LINES), REFERENCE_LINE[:, None], state_names={"Line": names["Line"]}),
        conditional("Shot", shot_table, ["Pressure", "BowlType", "Length", "Line"]),
        conditional("Outcome", outcome_table, ["Pressure", "Shot", "BowlType", "Length"]),
    )
    model.check_model()
    return model


def load_batter(player: str) -> BattingNetwork:
    if player not in BATTERS:
        raise ValueError(f"unknown batter {player!r}, expected one of {BATTERS}")
    counts = json.loads(BATTING_COUNTS.read_text())["players"]
    rates = observed_rates(player, counts, load_career_stats())
    shots = _shot_table(_aggression(player, counts))
    outcomes = _outcome_table(shots, rates, outcome_multipliers(player, BOWL_TYPES, OUTCOMES))
    return BattingNetwork(player, _build_model(shots, outcomes), shots, outcomes)
