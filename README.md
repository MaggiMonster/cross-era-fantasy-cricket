# Cross-Era Cricket Duel

A 2D cricket game where famous batsmen and bowlers are modelled as Bayesian
networks learned from real data, then played against each other.

University project by Apurva Verma (MaggiMonster) and Jaivin (JaivinB).

| Era | Batsman | Bowler |
|-----|---------|--------|
| Old | Sachin Tendulkar (1989-2013) | Shane Warne, leg-spin (1992-2007) |
| New | Virat Kohli (2008 onwards) | Jasprit Bumrah, fast (2016 onwards) |

Matchups are always old vs new: **Sachin vs Bumrah** and **Kohli vs Warne**.

## The game

The batsman chases a target with limited overs and lives (default 3 overs, 3
lives, all configurable). On each ball the bowler's network samples a delivery,
the batsman's network samples a shot, and an outcome model gives dot, 1, 2, 3, 4,
6 or a wicket type. Modes: human bats, human bowls, or auto.

## Status

| Part | Status |
|------|--------|
| Data pipeline, shared types, batting networks | done |
| Bowling networks, matchup outcome model | Turn 2 |
| Match engine, Pygame screen, batting controls | Turn 3 |
| Bowling view and controls, auto mode, menu, validation | Turn 4 |

The game is not playable yet.

## Setup

Python 3.12 on Apple Silicon, no GPU needed. Run from the repo root:

```sh
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests -q
.venv/bin/python -m duel.cricsheet   # optional: rebuild data from Cricsheet
```

## Docs

- [`docs/interface.md`](docs/interface.md) - types and network structure
- [`docs/assumptions.md`](docs/assumptions.md) - every prior and modelling choice
- [`HANDOFF.md`](HANDOFF.md) - whose turn it is
- [`archive/`](archive/README.md) - the old video-generation scope

## Data credit

Ball-by-ball data from [Cricsheet](https://cricsheet.org), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), filtered and aggregated
by us. Career figures are in `duel/data/career_stats.csv`, each with its source.
