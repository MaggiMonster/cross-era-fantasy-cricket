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
| 5 | Apurva | Character pipeline, Sachin and Kohli, eight batting shots, 3D batting controls | done |
| 6 | Jaivin | Bumrah and Warne, bowling actions and controls, auto mode, character select | done |
| 7 | Apurva | Shot direction, fielders, replays, camera cuts, final docs, demo | done |

Play the 3D game (needs Node.js):

```sh
cd web && npm install && npm run dev
```

Open <http://127.0.0.1:5173>. The game opens on a menu with character select, bat, bowl or
auto mode, overs and lives.

| Mode | Keys |
|------|------|
| Bat | Arrows: drive, defend, cut, work. Shift plus arrows: loft, sweep, leave, pull. `1`-`8` also work. Space lets the network choose. |
| Bowl | `1`-`5` length, arrows line, Enter or Space bowls |
| Any | `C` switches between the broadcast and close views. Space or Enter skips a replay. `R` plays again. |

After the bat, the ball goes where the shot and the networks' outcome say: fours find a gap
to the rope, sixes clear it, and catches go to a fielder. Nine rigged fielders, a keeper and the
bowler take the field, catch with both hands, and pick up and throw. Boundaries and wickets get a slow-motion replay, and the camera cuts
to follow the ball, the rope, the catcher or the stumps.

Players are rigged characters when their files exist in the local assets folder
(`~/cricket-project/assets/`, not in git), otherwise capsules. Faces are stylised, not likenesses.

**On a fresh clone the game plays fully, with capsule players and simple fielders.** The
networks, shots, ball paths, replays and cameras are all the same. To build the rigged
characters too, install Blender with the free MPFB extension and run the three scripts in
`pipeline/` (see [`docs/asset-pipeline.md`](docs/asset-pipeline.md)). Each takes a few seconds.

### How the networks drive the 3D game

1. The bowling network samples a delivery, or a human picks length and line.
2. The batting network picks a shot, or the human does.
3. The matchup model samples the outcome.
4. Only then is the ball drawn: its flight from the delivery, the swing steered to meet it,
   and its path after the bat chosen to fit the outcome. Visuals use their own random numbers,
   so they cannot change a result.

The network tables are exported to `web/public/data/networks.json`, and a test checks that the
JavaScript sampler gives the same probabilities and duels as Python.

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
.venv/bin/python -m pytest tests -q   # all tests pass on a fresh clone
```

The four-player Cricsheet extract (`data/cricsheet/balls.csv.gz`) is committed, so nothing
needs downloading. `python -m duel.cricsheet` rebuilds it from the latest Cricsheet archives,
but newer matches change some numbers. See [`data/README.md`](data/README.md) first.

### Reproduce the report's results

```sh
.venv/bin/python -m duel.validate    # 1000 duels per matchup, fixed seed
```

This rewrites [`docs/validation.md`](docs/validation.md), which holds the results table in the
project report: per-ball runs, wickets, boundaries and dots for each matchup against the log5
expectation, and the batsman's win rate. The seed is fixed, so the numbers come out the same.

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
