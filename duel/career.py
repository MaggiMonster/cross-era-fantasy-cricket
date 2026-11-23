"""Hand-entered career aggregates. Every row must name its source."""
from __future__ import annotations

import csv
from pathlib import Path

CAREER_CSV = Path(__file__).parent / "data" / "career_stats.csv"


def load_career_stats(path: Path = CAREER_CSV) -> dict[tuple[str, str, str], float]:
    stats = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if not row["source"].strip() or not row["as_of"].strip():
                raise ValueError(f"career stat without a source or date: {row}")
            key = (row["player"], row["format"], row["stat"])
            if key in stats:
                raise ValueError(f"duplicate career stat: {key}")
            stats[key] = float(row["value"])
    return stats
