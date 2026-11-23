"""Simulate 1000 duels per matchup, compare with real numbers, write docs/validation.md.

Run from the repo root: python -m duel.validate
"""
from __future__ import annotations

import csv
import gzip
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from duel import batting, bowling
from duel.batting import OUTCOMES, _vector
from duel.career import load_career_stats
from duel.cricsheet import BALLS_CSV, BATTING_COUNTS, BOWLING_COUNTS, PLAYERS
from duel.engine import Duel, default_target
from duel.matchup import MATCHUPS, load_matchup
from duel.pace_spin import load_bowler_types
from duel.types import OutcomeType

DUELS = 1000
SEED = 20261123
TOP_BOWLERS = 20
REPORT = Path(__file__).resolve().parent.parent / "docs" / "validation.md"
NAMES = {"tendulkar": "Tendulkar", "kohli": "Kohli", "bumrah": "Bumrah", "warne": "Warne"}
STYLE_LABEL = {"pace": "pace", "finger_spin": "finger spin", "wrist_spin": "wrist spin"}


def rates(tally: np.ndarray) -> dict[str, float]:
    """Per-ball rates from a tally ordered like OUTCOMES."""
    balls = tally.sum()
    index = {o: i for i, o in enumerate(OUTCOMES)}
    runs = sum(o.runs * tally[i] for i, o in enumerate(OUTCOMES))
    wickets = sum(tally[i] for i, o in enumerate(OUTCOMES) if o.is_wicket)
    return {
        "runs_per_ball": float(runs / balls),
        "wicket_rate": float(wickets / balls),
        "boundary_rate": float((tally[index[OutcomeType.FOUR]] + tally[index[OutcomeType.SIX]]) / balls),
        "dot_rate": float(tally[index[OutcomeType.DOT]] / balls),
    }


def expected_rates(batter: str, bowler: str, pressure_balls: Counter) -> dict[str, float]:
    """Log5 of the two players' real rates against the population, at the duel's pressure mix.

    This uses no line, length or shot priors, so it shows what the real records alone imply.
    """
    counts = json.loads(BATTING_COUNTS.read_text())["players"]
    data = bowling._load_counts()
    career = load_career_stats()
    bat = batting.observed_rates(batter, counts, career)
    bowl = bowling.observed_rates(bowler, data, career)
    population = bowling.population_rates(data)
    total = sum(pressure_balls.values())
    mixed = np.zeros(len(OUTCOMES))
    for pressure, balls in pressure_balls.items():
        p = bat[pressure] * bowl[pressure] / population[pressure]
        mixed += balls / total * p / p.sum()
    return rates(mixed)


def simulate(batter: str, bowler: str, duels: int = DUELS, seed: int = SEED) -> dict:
    matchup = load_matchup(batter, bowler)
    seeds = np.random.SeedSequence(seed).spawn(duels)
    tally = np.zeros(len(OUTCOMES))
    runs, wins, balls, wickets = [], 0, [], []
    endings: Counter[str] = Counter()
    pressure_balls: Counter = Counter()
    for s in seeds:
        game = Duel(matchup, seed=s)
        while not game.state.is_over:
            pressure_balls[game.state.pressure] += 1
            result = game.play()
            tally[OUTCOMES.index(result.outcome.kind)] += 1
        state = game.state
        wins += state.batter_won
        runs.append(state.runs)
        balls.append(state.balls_bowled)
        wickets.append(state.lives_lost)
        endings["target reached" if state.batter_won else "out of lives" if state.lives_left == 0 else "out of balls"] += 1
    p = wins / duels
    return {
        "target": default_target(batter),
        "win_rate": p,
        "win_margin": 1.96 * math.sqrt(p * (1 - p) / duels),
        "mean_runs": float(np.mean(runs)),
        "mean_balls": float(np.mean(balls)),
        "mean_wickets": float(np.mean(wickets)),
        "endings": endings,
        "rates": rates(tally),
        "expected": expected_rates(batter, bowler, pressure_balls),
        "balls": int(tally.sum()),
    }


def top_bowlers(batter: str, n: int = TOP_BOWLERS) -> list[tuple[str, int, str]]:
    """The bowlers who bowled the most legal balls to this batter in our Cricsheet data."""
    labels = load_bowler_types()
    faced: Counter[str] = Counter()
    with gzip.open(BALLS_CSV, "rt", newline="") as f:
        for row in csv.DictReader(f):
            if row["batter"] == PLAYERS[batter] and not int(row["wide"]):
                faced[row["bowler"]] += 1
    return [(name, balls, STYLE_LABEL.get(labels.get(name, ""), "NOT LABELLED")) for name, balls in faced.most_common(n)]


def _row(label: str, r: dict[str, float]) -> str:
    return (
        f"| {label} | {r['runs_per_ball']:.3f} | {r['wicket_rate'] * 100:.2f}% | "
        f"{r['boundary_rate'] * 100:.1f}% | {r['dot_rate'] * 100:.1f}% |"
    )


def outside_range(simulated: dict, batter: dict, bowler: dict) -> list[str]:
    """Rates where the duel falls outside the span of the two players' real IPL rates."""
    labels = {"runs_per_ball": "runs", "wicket_rate": "wickets", "boundary_rate": "boundaries", "dot_rate": "dots"}
    notes = []
    for key, label in labels.items():
        low, high = sorted((batter[key], bowler[key]))
        if not low <= simulated[key] <= high:
            notes.append(f"{label} ({'below' if simulated[key] < low else 'above'} both)")
    return notes


def report(results: dict, bowlers: dict) -> str:
    batting = json.loads(BATTING_COUNTS.read_text())["players"]
    bowling = json.loads(BOWLING_COUNTS.read_text())
    lines = [
        "# Validation",
        "",
        "Generated by `python -m duel.validate`. Do not edit by hand.",
        "",
        f"Each matchup is simulated for {DUELS} duels (3 overs, 3 lives, default target, seed {SEED}),",
        "with the networks choosing every delivery and shot.",
        "",
        "These matchups never happened, so there is no true answer to compare with. The real",
        "numbers below are each player's own record against everyone else. A duel is also a",
        "short chase that stops at the target, so its rates are not expected to equal a career rate.",
        "",
    ]
    for (batter, bowler), r in results.items():
        bat_ipl, bat_test = (rates(_vector(batting[batter][f]["all"])) for f in ("ipl", "tests"))
        bowl_ipl, bowl_test = (rates(_vector(bowling["players"][bowler][f]["all"])) for f in ("ipl", "tests"))
        ends = ", ".join(f"{k} {v / DUELS:.1%}" for k, v in r["endings"].most_common())
        outside = outside_range(r["rates"], bat_ipl, bowl_ipl)
        check = "Outside the two players' real IPL rates: " + ", ".join(outside) + "." if outside else "All four rates lie between the two players' real IPL rates."
        lines += [
            f"## {NAMES[batter]} vs {NAMES[bowler]}",
            "",
            f"- Target: **{r['target']}** from 18 balls.",
            f"- Batter wins **{r['win_rate']:.1%}** of duels (95% margin {r['win_margin'] * 100:.1f} points).",
            f"- Average duel: {r['mean_runs']:.1f} runs, {r['mean_balls']:.1f} balls, {r['mean_wickets']:.2f} lives lost.",
            f"- Endings: {ends}.",
            "",
            "| Per ball | Runs | Wicket | Boundary | Dot |",
            "|---|---|---|---|---|",
            _row(f"**Simulated duel** ({r['balls']} balls)", r["rates"]),
            _row("**Expected from real records (log5)**", r["expected"]),
            _row(f"{NAMES[batter]} real, IPL", bat_ipl),
            _row(f"{NAMES[bowler]} real, IPL", bowl_ipl),
            _row(f"{NAMES[batter]} real, Tests", bat_test),
            _row(f"{NAMES[bowler]} real, Tests", bowl_test),
            "",
            f"**Check:** {check} A matchup can correctly fall outside both when both players are on the same side of the IPL average.",
            "",
            f"**Against the log5 expectation:** simulated runs per ball differ by {r['rates']['runs_per_ball'] - r['expected']['runs_per_ball']:+.3f}.",
            "",
        ]
    lines += [
        "## Bowlers faced most, for checking labels",
        "",
        "Counts are legal balls in our Cricsheet Tests + IPL data, which misses Tendulkar's",
        "career before 2001. Labels come from `duel/data/bowler_types.csv` and were entered from",
        "general cricket knowledge. **Please check each one and tick it.**",
        "",
    ]
    for batter, rows in bowlers.items():
        lines += [f"### {NAMES[batter]}", "", "| # | Bowler | Balls | Label | Correct? |", "|---|---|---|---|---|"]
        lines += [f"| {i} | {name} | {balls} | {style} | [ ] |" for i, (name, balls, style) in enumerate(rows, 1)]
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    results = {m: simulate(*m) for m in MATCHUPS}
    bowlers = {b: top_bowlers(b) for b, _ in MATCHUPS}
    REPORT.write_text(report(results, bowlers))
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
