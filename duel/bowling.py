"""Bowling Bayesian networks. Structure in docs/interface.md, priors in docs/assumptions.md."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from pgmpy.factors.discrete import TabularCPD
from pgmpy.models import DiscreteBayesianNetwork

from duel.batting import (
    BOWL_TYPES,
    LENGTHS,
    LINES,
    OUTCOMES,
    PRESSURES,
    SMOOTHING_BALLS,
    TEST_WEIGHT,
    WICKET_MASK,
    _boundary_rate,
    _expit,
    _hazard,
    _logit,
    _outcome_table,
    _shot_table,
    _vector,
)
from duel.career import load_career_stats
from duel.cricsheet import BATTERS, BATTING_COUNTS, BOWLERS, BOWLING_COUNTS
from duel.types import BowlType, Delivery, Length, Line, MatchState, OutcomeType, Pressure

BOWL_TYPE = {"bumrah": BowlType.PACE, "warne": BowlType.SPIN}

# Prior P(Length | Pressure). Columns follow Length: yorker, full, good, short, bouncer.
LENGTH_PRIOR = {
    "bumrah": {
        Pressure.LOW: [0.08, 0.22, 0.45, 0.18, 0.07],
        Pressure.MEDIUM: [0.14, 0.22, 0.40, 0.17, 0.07],
        Pressure.HIGH: [0.30, 0.22, 0.28, 0.12, 0.08],
    },
    "warne": {
        Pressure.LOW: [0.01, 0.34, 0.50, 0.14, 0.01],
        Pressure.MEDIUM: [0.02, 0.38, 0.46, 0.13, 0.01],
        Pressure.HIGH: [0.03, 0.44, 0.40, 0.12, 0.01],
    },
}
# Prior P(Line | Length). Columns follow Line: outside_off, stumps, leg.
LINE_PRIOR = {
    "bumrah": {
        Length.YORKER: [0.15, 0.75, 0.10],
        Length.FULL: [0.40, 0.50, 0.10],
        Length.GOOD: [0.55, 0.37, 0.08],
        Length.SHORT: [0.45, 0.40, 0.15],
        Length.BOUNCER: [0.35, 0.45, 0.20],
    },
    "warne": {
        Length.YORKER: [0.20, 0.65, 0.15],
        Length.FULL: [0.40, 0.33, 0.27],
        Length.GOOD: [0.42, 0.33, 0.25],
        Length.SHORT: [0.45, 0.35, 0.20],
        Length.BOUNCER: [0.40, 0.40, 0.20],
    },
}


def _load_counts() -> dict:
    return json.loads(BOWLING_COUNTS.read_text())


def _blended_rates(side: dict, population: dict, test_hazard: float) -> dict[Pressure, np.ndarray]:
    """P(Outcome | Pressure) from IPL, shifted by Test skill. Mirrors batting.observed_rates."""
    ipl, tests = _vector(side["ipl"]["all"]), _vector(side["tests"]["all"])
    pop_ipl, pop_tests = _vector(population["ipl"]["all"]), _vector(population["tests"]["all"])
    relative_test = _logit(test_hazard) - _logit(_hazard(pop_tests))
    relative_ipl = _logit(_hazard(ipl)) - _logit(_hazard(pop_ipl))
    shift = TEST_WEIGHT * (relative_test - relative_ipl)

    mix = TEST_WEIGHT * tests[WICKET_MASK] / tests[WICKET_MASK].sum()
    mix = mix + (1 - TEST_WEIGHT) * ipl[WICKET_MASK] / ipl[WICKET_MASK].sum()
    mix = (mix + 1e-3) / (mix + 1e-3).sum()

    rates = {}
    for pressure in PRESSURES:
        group = _vector(side["ipl"].get(pressure.value, {}))
        smoothed = (group + SMOOTHING_BALLS * ipl / ipl.sum() + 0.5) / (
            group.sum() + SMOOTHING_BALLS + 0.5 * len(OUTCOMES)
        )
        hazard = _expit(_logit(_hazard(smoothed)) + shift)
        p = smoothed.copy()
        p[~WICKET_MASK] *= (1 - hazard) / p[~WICKET_MASK].sum()
        p[WICKET_MASK] = hazard * mix
        rates[pressure] = p
    return rates


def population_rates(data: dict) -> dict[Pressure, np.ndarray]:
    population = data["population"]
    return _blended_rates(population, population, _hazard(_vector(population["tests"]["all"])))


def observed_rates(player: str, data: dict, career: dict) -> dict[Pressure, np.ndarray]:
    """The bowler's outcome rates, with Test risk corrected to the career bowling average."""
    side = data["players"][player]
    window_average = side["test_runs_conceded"] / side["test_wickets"]
    correction = window_average / career[player, "tests", "bowling_average"]
    test_hazard = _hazard(_vector(side["tests"]["all"])) * correction
    return _blended_rates(side, data["population"], test_hazard)


@lru_cache(maxsize=1)
def baseline_table() -> np.ndarray:
    """P(Outcome | Pressure, BowlType, Length, Line) for an average batter and bowler.

    Built with the batting network's own pipeline from all Tests + IPL balls, so
    delivery effects cancel when the batter's table is divided by it.
    """
    data = _load_counts()
    batting = json.loads(BATTING_COUNTS.read_text())["players"]
    pooled = sum(_vector(batting[b]["ipl"]["all"]) for b in BATTERS)
    population_ipl = _vector(data["population"]["ipl"]["all"])
    aggression = float(np.log(_boundary_rate(population_ipl) / _boundary_rate(pooled)))
    shots = _shot_table(aggression)
    outcomes = _outcome_table(shots, population_rates(data))
    return np.einsum("pblms,psblo->pblmo", shots, outcomes)


def _delivery_tables(player: str) -> tuple[np.ndarray, np.ndarray]:
    lengths = np.array([LENGTH_PRIOR[player][p] for p in PRESSURES], dtype=float)
    lines = np.array([LINE_PRIOR[player][l] for l in LENGTHS], dtype=float)
    return lengths, lines


def _outcome_given_delivery(
    baseline: np.ndarray, lengths: np.ndarray, lines: np.ndarray, rates: dict[Pressure, np.ndarray]
) -> np.ndarray:
    """P(Outcome | Pressure, Length, Line): baseline scaled to the bowler's rates over their own mix."""
    table = np.zeros_like(baseline)
    for i, pressure in enumerate(PRESSURES):
        joint = lengths[i][:, None] * lines
        target = rates[pressure]
        scale = target / np.einsum("lm,lmo->o", joint, baseline[i])
        for _ in range(500):
            cell = baseline[i] * scale
            cell /= cell.sum(axis=-1, keepdims=True)
            marginal = np.einsum("lm,lmo->o", joint, cell)
            scale *= target / marginal
            if np.abs(marginal - target).max() < 1e-9:
                break
        table[i] = cell
    return table


@dataclass
class BowlingNetwork:
    player: str
    bowl_type: BowlType
    model: DiscreteBayesianNetwork
    length_table: np.ndarray
    line_table: np.ndarray
    outcome_table: np.ndarray

    def delivery_probs(self, pressure: Pressure) -> dict[tuple[Length, Line], float]:
        i = PRESSURES.index(pressure)
        joint = self.length_table[i][:, None] * self.line_table
        return {
            (length, line): float(joint[k, m])
            for k, length in enumerate(LENGTHS)
            for m, line in enumerate(LINES)
        }

    def sample_delivery(self, state: MatchState, rng: np.random.Generator) -> Delivery:
        i = PRESSURES.index(state.pressure)
        k = rng.choice(len(LENGTHS), p=self.length_table[i])
        m = rng.choice(len(LINES), p=self.line_table[k])
        return Delivery(self.bowl_type, LENGTHS[k], LINES[m])

    def outcome_probs(self, delivery: Delivery, pressure: Pressure) -> dict[OutcomeType, float]:
        if delivery.bowl_type != self.bowl_type:
            raise ValueError(f"{self.player} bowls {self.bowl_type.value}, got {delivery.bowl_type.value}")
        p = self.outcome_table[
            PRESSURES.index(pressure),
            LENGTHS.index(delivery.length),
            LINES.index(delivery.line),
        ]
        return dict(zip(OUTCOMES, p.tolist()))


def _build_model(
    lengths: np.ndarray, lines: np.ndarray, outcomes: np.ndarray
) -> DiscreteBayesianNetwork:
    names = {
        "Pressure": [p.value for p in PRESSURES],
        "Length": [l.value for l in LENGTHS],
        "Line": [l.value for l in LINES],
        "Outcome": [o.value for o in OUTCOMES],
    }
    model = DiscreteBayesianNetwork(
        [
            ("Pressure", "Length"), ("Length", "Line"),
            ("Pressure", "Outcome"), ("Length", "Outcome"), ("Line", "Outcome"),
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
        conditional("Length", lengths, ["Pressure"]),
        conditional("Line", lines, ["Length"]),
        conditional("Outcome", outcomes, ["Pressure", "Length", "Line"]),
    )
    model.check_model()
    return model


def load_bowler(player: str) -> BowlingNetwork:
    if player not in BOWLERS:
        raise ValueError(f"unknown bowler {player!r}, expected one of {BOWLERS}")
    rates = observed_rates(player, _load_counts(), load_career_stats())
    lengths, lines = _delivery_tables(player)
    bowl_type = BOWL_TYPE[player]
    baseline = baseline_table()[:, BOWL_TYPES.index(bowl_type)]
    outcomes = _outcome_given_delivery(baseline, lengths, lines, rates)
    return BowlingNetwork(player, bowl_type, _build_model(lengths, lines, outcomes), lengths, lines, outcomes)
