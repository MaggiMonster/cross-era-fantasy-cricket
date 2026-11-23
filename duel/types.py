"""Shared types for the duel. The contract is documented in docs/interface.md."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

SCHEMA_VERSION = "1.6"

# Required runs per over at which a chase becomes medium and high pressure.
PRESSURE_MEDIUM_RATE = 7.0
PRESSURE_HIGH_RATE = 10.0


class BowlType(str, Enum):
    PACE = "pace"
    SPIN = "spin"


class Length(str, Enum):
    YORKER = "yorker"
    FULL = "full"
    GOOD = "good"
    SHORT = "short"
    BOUNCER = "bouncer"


class Line(str, Enum):
    OUTSIDE_OFF = "outside_off"
    STUMPS = "stumps"
    LEG = "leg"


class ShotType(str, Enum):
    LEAVE = "leave"
    DEFEND = "defend"
    WORK = "work"
    DRIVE = "drive"
    CUT = "cut"
    PULL = "pull"
    SWEEP = "sweep"
    LOFT = "loft"


class Pressure(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OutcomeType(str, Enum):
    DOT = "dot"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    SIX = "6"
    BOWLED = "bowled"
    LBW = "lbw"
    CAUGHT = "caught"
    STUMPED = "stumped"
    RUN_OUT = "run_out"

    @property
    def runs(self) -> int:
        return int(self.value) if self.value.isdigit() else 0

    @property
    def is_wicket(self) -> bool:
        return self in WICKETS


WICKETS = frozenset(
    {
        OutcomeType.BOWLED,
        OutcomeType.LBW,
        OutcomeType.CAUGHT,
        OutcomeType.STUMPED,
        OutcomeType.RUN_OUT,
    }
)


@dataclass(frozen=True)
class Delivery:
    bowl_type: BowlType
    length: Length
    line: Line


@dataclass(frozen=True)
class Shot:
    shot_type: ShotType


@dataclass(frozen=True)
class Outcome:
    kind: OutcomeType

    @property
    def runs(self) -> int:
        return self.kind.runs

    @property
    def is_wicket(self) -> bool:
        return self.kind.is_wicket


def pressure_for_rate(required_rate: float) -> Pressure:
    if required_rate >= PRESSURE_HIGH_RATE:
        return Pressure.HIGH
    if required_rate >= PRESSURE_MEDIUM_RATE:
        return Pressure.MEDIUM
    return Pressure.LOW


@dataclass(frozen=True)
class MatchState:
    """The duel before a ball. Defaults are 3 overs and 3 lives."""

    target: int
    overs: int = 3
    lives: int = 3
    runs: int = 0
    balls_bowled: int = 0
    lives_lost: int = 0

    @property
    def balls_left(self) -> int:
        return max(self.overs * 6 - self.balls_bowled, 0)

    @property
    def runs_needed(self) -> int:
        return max(self.target - self.runs, 0)

    @property
    def lives_left(self) -> int:
        return max(self.lives - self.lives_lost, 0)

    @property
    def required_rate(self) -> float:
        if self.runs_needed == 0:
            return 0.0
        if self.balls_left == 0:
            return math.inf
        return self.runs_needed * 6 / self.balls_left

    @property
    def pressure(self) -> Pressure:
        return pressure_for_rate(self.required_rate)

    @property
    def batter_won(self) -> bool:
        return self.runs >= self.target

    @property
    def is_over(self) -> bool:
        return self.batter_won or self.balls_left == 0 or self.lives_left == 0
