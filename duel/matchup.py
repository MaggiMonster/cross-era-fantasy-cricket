"""Per-ball outcome for a batter and bowler who never met. Method in docs/assumptions.md."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from duel.batting import BOWL_TYPES, LENGTHS, LINES, OUTCOMES, PRESSURES, BattingNetwork, load_batter
from duel.bowling import BowlingNetwork, baseline_table, load_bowler
from duel.types import Delivery, MatchState, Outcome, OutcomeType, Pressure, Shot

MATCHUPS = (("tendulkar", "bumrah"), ("kohli", "warne"))


@dataclass
class Matchup:
    batter: BattingNetwork
    bowler: BowlingNetwork
    baseline: np.ndarray

    def baseline_probs(self, delivery: Delivery, pressure: Pressure) -> np.ndarray:
        return self.baseline[
            PRESSURES.index(pressure),
            BOWL_TYPES.index(delivery.bowl_type),
            LENGTHS.index(delivery.length),
            LINES.index(delivery.line),
        ]

    def outcome_probs(
        self, delivery: Delivery, shot: Shot, pressure: Pressure
    ) -> dict[OutcomeType, float]:
        """P(o) proportional to batter(o) * bowler(o) / baseline(o), all given this delivery."""
        batter = np.array(list(self.batter.outcome_probs(delivery, shot, pressure).values()))
        bowler = np.array(list(self.bowler.outcome_probs(delivery, pressure).values()))
        p = batter * bowler / self.baseline_probs(delivery, pressure)
        return dict(zip(OUTCOMES, (p / p.sum()).tolist()))

    def sample_outcome(
        self, delivery: Delivery, shot: Shot, state: MatchState, rng: np.random.Generator
    ) -> Outcome:
        probs = self.outcome_probs(delivery, shot, state.pressure)
        return Outcome(OUTCOMES[rng.choice(len(OUTCOMES), p=list(probs.values()))])


def load_matchup(batter: str, bowler: str) -> Matchup:
    if (batter, bowler) not in MATCHUPS:
        raise ValueError(f"matchups are old vs new, expected one of {MATCHUPS}")
    return Matchup(load_batter(batter), load_bowler(bowler), baseline_table())
