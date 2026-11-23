# Interface: how the batting and bowling halves connect

- **Schema version:** `1.5`
- **Reference implementation:** `duel/types.py`
- Change this file only together with `duel/types.py`, and bump `SCHEMA_VERSION`.

## Types

| Type | Fields / values |
|------|-----------------|
| `BowlType` | `pace`, `spin` |
| `Length` | `yorker`, `full`, `good`, `short`, `bouncer` |
| `Line` | `outside_off`, `stumps`, `leg` |
| `Delivery` | `bowl_type`, `length`, `line` |
| `ShotType` | `leave`, `defend`, `work`, `drive`, `cut`, `pull`, `sweep`, `loft` |
| `Shot` | `shot_type` |
| `OutcomeType` | `dot`, `1`, `2`, `3`, `4`, `6`, `bowled`, `lbw`, `caught`, `stumped`, `run_out` |
| `Outcome` | `kind`, plus derived `runs` and `is_wicket` |
| `Pressure` | `low` (required rate under 7), `medium` (7 to under 10), `high` (10 or more) |
| `MatchState` | `target`, `overs=3`, `lives=3`, `runs`, `balls_bowled`, `lives_lost`, plus derived `balls_left`, `runs_needed`, `lives_left`, `required_rate`, `pressure`, `batter_won`, `is_over` |

## One ball

```text
MatchState -> Pressure
Bowling network  -> Delivery
Batting network  -> Shot     given Delivery, Pressure
Outcome model    -> Outcome  given Delivery, Shot, Pressure, both players
```

## Batting network (done, `duel/batting.py`)

```text
Pressure, BowlType, Length, Line -> Shot
BowlType -> Length
Pressure, Shot, BowlType, Length -> Outcome
```

```python
from duel.batting import load_batter

net = load_batter("tendulkar")           # or "kohli"
shot = net.sample_shot(delivery, state, rng)
probs = net.outcome_probs(delivery, shot, state.pressure)  # {OutcomeType: p}
```

`net.model` is the pgmpy `DiscreteBayesianNetwork`. Its delivery CPDs are a
reference mix for calibration only. In a match, the delivery is evidence.

## Bowling network (done, `duel/bowling.py`)

```text
Pressure -> Length -> Line
Pressure, Length, Line -> Outcome
```

```python
from duel.bowling import load_bowler

net = load_bowler("bumrah")              # or "warne"
delivery = net.sample_delivery(state, rng)
probs = net.outcome_probs(delivery, state.pressure)  # {OutcomeType: p}
```

Bowling type is fixed per bowler, so `outcome_probs` raises `ValueError` for a
delivery of the other type.

## Matchup model (done, `duel/matchup.py`)

Provides `P(Outcome | Delivery, Shot, Pressure, batter, bowler)`. The method is in
`docs/assumptions.md`, section "Combining batter and bowler". A leave is then adjusted by
line and length, as described in the section "Leaving the ball".

```python
from duel.matchup import load_matchup

duel = load_matchup("tendulkar", "bumrah")   # or ("kohli", "warne")
delivery = duel.bowler.sample_delivery(state, rng)
shot = duel.batter.sample_shot(delivery, state, rng)
outcome = duel.sample_outcome(delivery, shot, state, rng)  # Outcome
probs = duel.outcome_probs(delivery, shot, state.pressure)  # {OutcomeType: p}
```

## Match engine (done, `duel/engine.py`)

```python
from duel.engine import Duel

game = Duel(load_matchup("kohli", "warne"), target=None, overs=3, lives=3, seed=1)
while not game.state.is_over:
    delivery = game.next_delivery()      # stable until the ball is played
    result = game.play(shot=None)        # None: the batting network chooses
```

`result` is a `BallResult` with `delivery`, `shot`, `outcome`, `before` and `after`.
`target=None` uses `default_target(batter, overs)`.

## Game screen (done for human batting, `duel/game.py`)

```sh
.venv/bin/python -m duel.game --matchup kohli-warne --overs 3 --lives 3
```

Keys: `1` to `8` choose a shot, `R` replays after a duel, `Esc` quits.

## Browser game (Turn 4, `web/`)

`python -m duel.export_web` writes every network table to `web/public/data/networks.json`.
Tables are flat, row-major arrays, and the `axes` field lists their order. Re-run it
whenever a network changes. `tests/test_web_sampler.py` fails if the file is stale.

```js
import { Duel, Networks, mulberry32 } from "./model/duel.js";

const networks = new Networks(await (await fetch("data/networks.json")).json());
const game = new Duel(networks, "kohli", "warne", { overs: 3, lives: 3, random: mulberry32(1) });
while (!game.isOver) {
  const delivery = game.nextDelivery();
  const result = game.play(null);   // or a shot name; null lets the network choose
}
```

`web/src/sim/ball.js` turns a delivery into a 3D path. It is presentation only and has
its own random generator, so it cannot change a result. Characters replace the capsules
in `web/src/scene/players.js` by keeping `root`, `reset`, `update(dt)`, `setSwing` and
`setRunUp`. `setSwing(shot, f)` takes `f` from 0 to 1 over `SWING.time`, with bat contact
at `SWING.lead` seconds. `createBatter` is async and falls back to a capsule.

```sh
cd web && npm install && npm run dev   # http://127.0.0.1:5173
```

URL options: `?matchup=kohli-warne&seed=1&auto=1&overs=3&lives=3`.
