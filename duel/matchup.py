"""Per-ball outcome for a batter and bowler who never met. Method in docs/assumptions.md."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from duel.batting import BOWL_TYPES, LENGTHS, LINES, OUTCOMES, PRESSURES, BattingNetwork, load_batter
from duel.bowling import BowlingNetwork, baseline_table, load_bowler
from duel.types import Delivery, Length, Line, MatchState, Outcome, OutcomeType, Pressure, Shot, ShotType

MATCHUPS = (("tendulkar", "bumrah"), ("kohli", "warne"))

# Prior P(bowled or lbw | the batter leaves this line and length), for average players.
LEAVE_RISK_BY_LINE = {
    Line.OUTSIDE_OFF: {Length.YORKER: 0.015, Length.FULL: 0.012, Length.GOOD: 0.010, Length.SHORT: 0.007, Length.BOUNCER: 0.002},
    Line.STUMPS: {Length.YORKER: 0.35, Length.FULL: 0.30, Length.GOOD: 0.18, Length.SHORT: 0.06, Length.BOUNCER: 0.005},
    Line.LEG: {Length.YORKER: 0.006, Length.FULL: 0.005, Length.GOOD: 0.004, Length.SHORT: 0.002, Length.BOUNCER: 0.001},
}
LEAVE_RISK = np.array([[LEAVE_RISK_BY_LINE[m][l] for l in LENGTHS] for m in LINES])  # (Line, Length)
# Limits on how far the two players' wicket records can move the odds of that risk.
LEAVE_SKILL_LIMITS = (0.5, 2.0)
_WICKETS = np.array([o.is_wicket for o in OUTCOMES])
_DOT, _BOWLED, _LBW, _STUMPED = (
    OUTCOMES.index(o) for o in (OutcomeType.DOT, OutcomeType.BOWLED, OutcomeType.LBW, OutcomeType.STUMPED)
)


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
        base = self.baseline_probs(delivery, pressure)
        p = batter * bowler / base
        p = p / p.sum()
        if shot.shot_type is ShotType.LEAVE:
            p = self._leave_probs(delivery, pressure, p, bowler, base)
        return dict(zip(OUTCOMES, p.tolist()))

    def _leave_probs(
        self, delivery: Delivery, pressure: Pressure, p: np.ndarray, bowler: np.ndarray, base: np.ndarray
    ) -> np.ndarray:
        """A leave cannot score or be caught. Its risk depends on line and length."""
        batter_wicket = sum(
            weight * sum(v for o, v in self.batter.outcome_probs(delivery, Shot(s), pressure).items() if o.is_wicket)
            for s, weight in self.batter.shot_probs(delivery, pressure).items()
        )
        base_wicket = base[_WICKETS].sum()
        skill = np.clip(batter_wicket / base_wicket * bowler[_WICKETS].sum() / base_wicket, *LEAVE_SKILL_LIMITS)
        prior = LEAVE_RISK[LINES.index(delivery.line), LENGTHS.index(delivery.length)]
        odds = prior / (1 - prior) * skill
        risk = odds / (1 + odds)
        share = p[_BOWLED] / (p[_BOWLED] + p[_LBW])
        result = np.zeros(len(OUTCOMES))
        result[_BOWLED], result[_LBW], result[_STUMPED] = risk * share, risk * (1 - share), p[_STUMPED]
        result[_DOT] = 1 - risk - p[_STUMPED]
        return result

    def sample_outcome(
        self, delivery: Delivery, shot: Shot, state: MatchState, rng: np.random.Generator
    ) -> Outcome:
        probs = self.outcome_probs(delivery, shot, state.pressure)
        return Outcome(OUTCOMES[rng.choice(len(OUTCOMES), p=list(probs.values()))])


def load_matchup(batter: str, bowler: str) -> Matchup:
    if (batter, bowler) not in MATCHUPS:
        raise ValueError(f"matchups are old vs new, expected one of {MATCHUPS}")
    return Matchup(load_batter(batter), load_bowler(bowler), baseline_table())
