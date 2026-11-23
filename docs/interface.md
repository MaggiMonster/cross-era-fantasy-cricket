# Interface: how the batting and bowling halves connect

- **Schema version:** `1.0`
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

## Bowling network (Turn 2, `duel/bowling.py`)

Must provide `load_bowler(player)` for `"bumrah"` and `"warne"`, and:

- `sample_delivery(state, rng) -> Delivery`
- `outcome_probs(delivery, pressure) -> {OutcomeType: p}`, the bowler's tendency
  over the same outcome states

## Matchup model (Turn 2)

Must provide `P(Outcome | Delivery, Shot, Pressure, batter, bowler)`. The planned
method is in `docs/assumptions.md`, section "Combining batter and bowler".
