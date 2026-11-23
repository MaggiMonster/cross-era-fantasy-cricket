# Cross-Era Cricket Duel

A 3D browser cricket game where famous batsmen and bowlers are modelled as Bayesian
networks learned from real data, then played against each other. The original 2D
Pygame version stays as a working fallback.

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

| Turn | Who | Part | Status |
|------|-----|------|--------|
| 1-3 | Both | Data, networks, outcome model, match engine, Pygame game | done |
| 4 | Jaivin | Three.js stadium, ball physics, JS sampler, capsule players, validation, asset research | done |
| 5 | Apurva | Character pipeline, Sachin and Kohli, eight batting shots, 3D batting controls | next |
| 6 | Jaivin | Bumrah and Warne, bowling actions and controls, auto mode, character select | planned |
| 7 | Apurva | Shot direction, fielders, replays, camera cuts, final docs, demo | planned |

Play the 3D game (needs Node.js):

```sh
cd web && npm install && npm run dev
```

Open <http://127.0.0.1:5173>. Keys `1` to `8` play a shot, and Space lets the network
choose. Players are placeholder capsules until Turns 5 and 6.

The 2D fallback:

```sh
.venv/bin/python -m duel.game --matchup tendulkar-bumrah
.venv/bin/python -m duel.game --matchup kohli-warne
```

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
- [`docs/validation.md`](docs/validation.md) - 1000-duel results and bowler label check
- [`docs/asset-pipeline.md`](docs/asset-pipeline.md) - motion capture and face methods, asset storage
- [`HANDOFF.md`](HANDOFF.md) - whose turn it is
- [`archive/`](archive/README.md) - the old video-generation scope

## Data credit

Ball-by-ball data from [Cricsheet](https://cricsheet.org), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), filtered and aggregated
by us. Career figures are in `duel/data/career_stats.csv`, each with its source.
