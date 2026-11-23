"""Match engine: overs, lives, target and ball-by-ball sampling."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace

import numpy as np

from duel.batting import OUTCOMES, _vector
from duel.cricsheet import BATTING_COUNTS
from duel.matchup import Matchup
from duel.types import Delivery, MatchState, Outcome, Shot


def default_target(batter: str, overs: int = 3) -> int:
    """Runs to win: one more than the batter's real IPL scoring rate over these balls."""
    counts = json.loads(BATTING_COUNTS.read_text())["players"]
    tally = _vector(counts[batter]["ipl"]["all"])
    runs_per_ball = sum(o.runs * n for o, n in zip(OUTCOMES, tally)) / tally.sum()
    return math.floor(runs_per_ball * overs * 6) + 1


@dataclass(frozen=True)
class BallResult:
    delivery: Delivery
    shot: Shot
    outcome: Outcome
    before: MatchState
    after: MatchState


class Duel:
    """One chase. Call next_delivery, then play with a shot, or None to let the network choose."""

    def __init__(
        self,
        matchup: Matchup,
        target: int | None = None,
        overs: int = 3,
        lives: int = 3,
        seed: int | None = None,
    ):
        if overs < 1 or lives < 1:
            raise ValueError("overs and lives must be at least 1")
        if target is None:
            target = default_target(matchup.batter.player, overs)
        if target < 1:
            raise ValueError("target must be at least 1")
        self.matchup = matchup
        self.state = MatchState(target=target, overs=overs, lives=lives)
        self.rng = np.random.default_rng(seed)
        self.delivery: Delivery | None = None
        self.history: list[BallResult] = []

    def next_delivery(self) -> Delivery:
        if self.state.is_over:
            raise RuntimeError("the duel is over")
        if self.delivery is None:
            self.delivery = self.matchup.bowler.sample_delivery(self.state, self.rng)
        return self.delivery

    def play(self, shot: Shot | None = None) -> BallResult:
        delivery = self.next_delivery()
        before = self.state
        if shot is None:
            shot = self.matchup.batter.sample_shot(delivery, before, self.rng)
        outcome = self.matchup.sample_outcome(delivery, shot, before, self.rng)
        self.state = replace(
            before,
            runs=before.runs + outcome.runs,
            balls_bowled=before.balls_bowled + 1,
            lives_lost=before.lives_lost + int(outcome.is_wicket),
        )
        self.delivery = None
        result = BallResult(delivery, shot, outcome, before, self.state)
        self.history.append(result)
        return result
