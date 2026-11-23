"""Download and parse Cricsheet ball-by-ball data (CC BY 4.0, cricsheet.org).

Run from the repo root: python -m duel.cricsheet
"""
from __future__ import annotations

import csv
import gzip
import json
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator

from duel.types import OutcomeType, pressure_for_rate

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cricsheet"
BALLS_CSV = DATA_DIR / "balls.csv.gz"
BATTING_COUNTS = Path(__file__).parent / "data" / "batting_counts.json"

FORMATS = ("tests", "ipl")
URL = "https://cricsheet.org/downloads/{fmt}_json.zip"

PLAYERS = {
    "tendulkar": "SR Tendulkar",
    "kohli": "V Kohli",
    "bumrah": "JJ Bumrah",
    "warne": "SK Warne",
}
BATTERS = ("tendulkar", "kohli")

DISMISSALS = {
    "bowled": OutcomeType.BOWLED,
    "hit wicket": OutcomeType.BOWLED,
    "lbw": OutcomeType.LBW,
    "caught": OutcomeType.CAUGHT,
    "caught and bowled": OutcomeType.CAUGHT,
    "stumped": OutcomeType.STUMPED,
    "run out": OutcomeType.RUN_OUT,
}
RUNS = {
    0: OutcomeType.DOT,
    1: OutcomeType.ONE,
    2: OutcomeType.TWO,
    3: OutcomeType.THREE,
    4: OutcomeType.FOUR,
    5: OutcomeType.FOUR,
    6: OutcomeType.SIX,
}

FIELDS = (
    "match_id", "format", "date", "innings", "over", "batter", "bowler",
    "batter_runs", "total_runs", "wide", "noball", "dismissal", "required_rate",
)


def overs_to_balls(overs: float) -> int:
    """Cricket notation: 19.3 overs is 19 overs and 3 balls."""
    whole, _, part = str(overs).partition(".")
    return int(whole) * 6 + int(part or 0)


def parse_match(match: dict, match_id: str, fmt: str) -> Iterator[dict]:
    """Yield one row per delivery, skipping super overs."""
    date = str(match["info"]["dates"][0])
    for number, innings in enumerate(match.get("innings", []), 1):
        if innings.get("super_over"):
            continue
        target = innings.get("target") or {}
        target_runs = target.get("runs")
        target_balls = overs_to_balls(target["overs"]) if "overs" in target else None
        scored = legal = 0
        for over in innings.get("overs", []):
            for ball in over["deliveries"]:
                extras = ball.get("extras", {})
                wide, noball = "wides" in extras, "noballs" in extras
                rate = None
                if target_runs is not None and target_balls is not None:
                    balls_left = target_balls - legal
                    if balls_left > 0:
                        rate = max(target_runs - scored, 0) * 6 / balls_left
                dismissal = next(
                    (
                        w["kind"]
                        for w in ball.get("wickets", [])
                        if w["player_out"] == ball["batter"] and w["kind"] in DISMISSALS
                    ),
                    "",
                )
                yield {
                    "match_id": match_id,
                    "format": fmt,
                    "date": date,
                    "innings": number,
                    "over": over["over"],
                    "batter": ball["batter"],
                    "bowler": ball["bowler"],
                    "batter_runs": ball["runs"]["batter"],
                    "total_runs": ball["runs"]["total"],
                    "wide": int(wide),
                    "noball": int(noball),
                    "dismissal": dismissal,
                    "required_rate": "" if rate is None else round(rate, 4),
                }
                scored += ball["runs"]["total"]
                legal += not (wide or noball)


def batter_outcome(row: dict) -> OutcomeType | None:
    """The batter's outcome for a ball, or None for a wide (not faced)."""
    if int(row["wide"]):
        return None
    if row["dismissal"]:
        return DISMISSALS[row["dismissal"]]
    return RUNS[min(int(row["batter_runs"]), 6)]


def batting_counts(rows: Iterable[dict]) -> dict:
    """Outcome counts per batter: by format, and by pressure in IPL chases."""
    names = {PLAYERS[key]: key for key in BATTERS}
    tallies: dict[tuple, Counter] = {}
    for row in rows:
        key = names.get(row["batter"])
        outcome = batter_outcome(row)
        if key is None or outcome is None:
            continue
        tallies.setdefault((key, row["format"], "all"), Counter())[outcome.value] += 1
        if row["format"] == "ipl" and row["required_rate"] != "":
            pressure = pressure_for_rate(float(row["required_rate"])).value
            tallies.setdefault((key, "ipl", pressure), Counter())[outcome.value] += 1
    counts: dict = {key: {fmt: {} for fmt in FORMATS} for key in BATTERS}
    for (key, fmt, group), tally in sorted(tallies.items()):
        counts[key][fmt][group] = dict(sorted(tally.items()))
    return counts


def download(fmt: str, data_dir: Path = DATA_DIR) -> Path:
    path = data_dir / f"{fmt}.zip"
    if not path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            URL.format(fmt=fmt), headers={"User-Agent": "cross-era-cricket-student-project"}
        )
        partial = path.with_suffix(".part")
        with urllib.request.urlopen(request) as response, open(partial, "wb") as f:
            f.write(response.read())
        partial.replace(path)
    return path


def iter_zip(path: Path, fmt: str) -> Iterator[dict]:
    """Read matches straight from the archive, without extracting it."""
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if name.endswith(".json"):
                yield from parse_match(json.loads(archive.read(name)), Path(name).stem, fmt)


def build() -> None:
    wanted = set(PLAYERS.values())
    rows = []
    for fmt in FORMATS:
        rows.extend(
            r for r in iter_zip(download(fmt), fmt) if r["batter"] in wanted or r["bowler"] in wanted
        )
    with gzip.open(BALLS_CSV, "wt", newline="") as f:
        writer = csv.DictWriter(f, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    output = {
        "source": "Cricsheet (cricsheet.org), CC BY 4.0; aggregated into outcome counts",
        "players": batting_counts(rows),
    }
    BATTING_COUNTS.write_text(json.dumps(output, indent=1) + "\n")
    print(f"{len(rows)} balls -> {BALLS_CSV.relative_to(ROOT)}, {BATTING_COUNTS.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
