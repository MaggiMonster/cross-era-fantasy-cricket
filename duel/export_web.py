"""Export the Bayesian network tables to JSON for the browser game.

Run from the repo root: python -m duel.export_web
Tables are flattened in row-major order, with the axes listed under each table.
Floats are written at full precision, so the JS sampler uses the same numbers.
"""
from __future__ import annotations

import json
from pathlib import Path

from duel.batting import BOWL_TYPES, LENGTHS, LINES, OUTCOMES, PRESSURES, SHOTS, _vector, load_batter
from duel.bowling import baseline_table, load_bowler
from duel.cricsheet import BATTERS, BATTING_COUNTS, BOWLERS
from duel.matchup import MATCHUPS
from duel.types import PRESSURE_HIGH_RATE, PRESSURE_MEDIUM_RATE, SCHEMA_VERSION

WEB_NETWORKS = Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "networks.json"


def _flat(table) -> list[float]:
    return table.ravel().tolist()


def build_export() -> dict:
    counts = json.loads(BATTING_COUNTS.read_text())["players"]
    batters = {}
    for name in BATTERS:
        net = load_batter(name)
        tally = _vector(counts[name]["ipl"]["all"])
        batters[name] = {
            "runs_per_ball": float(sum(o.runs * n for o, n in zip(OUTCOMES, tally)) / tally.sum()),
            "shot": _flat(net.shot_table),
            "outcome": _flat(net.outcome_table),
        }
    bowlers = {}
    for name in BOWLERS:
        net = load_bowler(name)
        bowlers[name] = {
            "bowl_type": net.bowl_type.value,
            "length": _flat(net.length_table),
            "line": _flat(net.line_table),
            "outcome": _flat(net.outcome_table),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "credit": "Ball-by-ball data from Cricsheet (cricsheet.org), CC BY 4.0, aggregated by us.",
        "states": {
            "pressure": [p.value for p in PRESSURES],
            "bowl_type": [b.value for b in BOWL_TYPES],
            "length": [l.value for l in LENGTHS],
            "line": [l.value for l in LINES],
            "shot": [s.value for s in SHOTS],
            "outcome": [o.value for o in OUTCOMES],
        },
        "axes": {
            "batter.shot": ["pressure", "bowl_type", "length", "line", "shot"],
            "batter.outcome": ["pressure", "shot", "bowl_type", "length", "outcome"],
            "bowler.length": ["pressure", "length"],
            "bowler.line": ["length", "line"],
            "bowler.outcome": ["pressure", "length", "line", "outcome"],
            "baseline": ["pressure", "bowl_type", "length", "line", "outcome"],
        },
        "pressure_rates": {"medium": PRESSURE_MEDIUM_RATE, "high": PRESSURE_HIGH_RATE},
        "wickets": [o.value for o in OUTCOMES if o.is_wicket],
        "matchups": [list(m) for m in MATCHUPS],
        "batters": batters,
        "bowlers": bowlers,
        "baseline": _flat(baseline_table()),
    }


def main() -> None:
    WEB_NETWORKS.parent.mkdir(parents=True, exist_ok=True)
    WEB_NETWORKS.write_text(json.dumps(build_export(), separators=(",", ":")) + "\n")
    print(f"wrote {WEB_NETWORKS} ({WEB_NETWORKS.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
