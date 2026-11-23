# Assumptions

Every modelling choice that is not read directly from data. Numbers marked
**prior** are our judgement and have not been measured.

## Data

1. **Formats: Tests + IPL** (decided by Apurva, Turn 1). ODIs have only 120 Warne
   balls and T20 internationals have none. Tests supply skill and IPL supplies
   attacking tempo.
2. **Coverage gaps.** Cricsheet has Tendulkar's Tests only from 2001 and IPL only
   at ages 34-40. His early career is missing from ball-by-ball data.
3. **Career correction.** Test dismissal risk per ball is multiplied by
   (Cricsheet average / career average), using `duel/data/career_stats.csv`.
4. **Outcome mapping.** Caught and bowled counts as caught, hit wicket as bowled,
   and 5 runs as a 4. Byes and leg byes are dots for the batter. Wides are not
   balls faced. Retirements are not dismissals.
5. **Striker only.** A non-striker's run-out is not charged, since a duel has one batter.

## Batting network

6. **Pressure** comes from the required rate in IPL chases: low under 7, medium 7
   to under 10, high 10 or more (**prior** thresholds).
7. **Smoothing.** Each pressure group gets 100 pseudo-balls of the player's overall
   IPL rates. This matters most for Tendulkar's high-pressure group (94 balls).
   Remaining noise is kept: his low-pressure dismissal rate is above his medium one.
8. **Skill blend.** Dismissal log-odds shift by `TEST_WEIGHT` (0.5, **prior**) times
   the player's relative Test risk minus relative IPL risk. "Relative" means against
   Tendulkar and Kohli pooled, which avoids comparing with tailenders.
9. **Dismissal mix** is 50% Tests and 50% IPL (same weight).
10. **No line, length or shot data exists.** These tables in `duel/batting.py` are
    **priors**: `SHOT_BY_LENGTH`, `SHOT_BY_LINE`, `SHOT_BY_BOWL`, `SHOT_ATTACK`,
    `PRESSURE_TILT`, `SHOT_EFFECT`, `LENGTH_EFFECT`, `BOWL_EFFECT`.
11. **Player adjustment.** Shot choice is tilted by the log ratio of the player's
    IPL boundary rate to the pooled rate.
12. **Calibration.** Outcome tables are scaled so that, over a **prior** reference
    delivery mix (`REFERENCE_*`), they reproduce the player's observed rates at each
    pressure. Against a real bowler's mix, rates will differ by design.
13. **Pace vs spin is not learned.** Cricsheet does not label bowling type, so
    batter differences against pace and spin are not measured. The effect is the
    same **prior** for both batsmen.
14. **Lives do not change behaviour.** Only the required rate sets pressure.

## Combining batter and bowler

These matchups never happened, so ball-by-ball results cannot be observed. The
planned method (implemented in Turn 2) is the generalised log5 / odds-ratio rule:

```text
P(o) proportional to batter(o) * bowler(o) / baseline(o)
```

`baseline` is the average rate of the comparison population, computed the same
way for both sides. A batter and bowler who are both average then give the
baseline, and each player's deviation from average carries through.
