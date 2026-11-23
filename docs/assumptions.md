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
method (`duel/matchup.py`) is the generalised log5 / odds-ratio rule, applied for
each specific delivery:

```text
P(o | d, s, p) proportional to batter(o | d, s, p) * bowler(o | d, p) / baseline(o | d, p)
```

`baseline` is the average rate of the comparison population, computed the same
way for both sides. A batter and bowler who are both average then give the
baseline, and each player's deviation from average carries through.

21. **Baseline population** is every ball in the Cricsheet Tests + IPL archives,
    all batters and bowlers. It goes through the same smoothing, Test/IPL blend and
    batting tables as a player.
22. **The baseline depends on the delivery.** Both the batter's and the bowler's
    tables contain the same delivery effects (for example, yorkers hit the stumps
    more). Dividing by a delivery-specific baseline stops those effects being
    counted twice.
23. **Independence.** Log5 assumes batter and bowler deviations combine without
    interaction. A specific batter's weakness against a specific bowling style is
    not modelled.
24. **Only two matchups are allowed:** Tendulkar vs Bumrah and Kohli vs Warne.

## Bowling network

15. **Structure** (`duel/bowling.py`): Pressure -> Length -> Line, and Pressure,
    Length, Line -> Outcome. Bowling type is fixed per bowler: Bumrah pace, Warne
    leg-spin, as listed on their Wikipedia profiles.
16. **No line or length data exists.** `LENGTH_PRIOR` and `LINE_PRIOR` are
    **priors**. Bumrah bowls more yorkers as pressure rises. Warne bowls fuller and
    uses the leg-side line more than Bumrah.
17. **Outcome rates are measured.** Each bowler's IPL rates by pressure use the same
    100-ball smoothing, `TEST_WEIGHT` and 50/50 dismissal mix as the batters. Risk is
    relative to the whole population, because a bowler faces all kinds of batter.
18. **Career correction.** Test wicket risk per ball is multiplied by (Cricsheet
    bowling average / career bowling average). Cricsheet has Bumrah's full Test
    record to date, but Warne's Tests only from 2004 to 2007.
19. **Run-outs stay in the outcome states** for the shared format, but they do not
    count as the bowler's wickets in the career correction. Byes and leg byes are not
    charged to the bowler.
20. **Small samples remain noisy.** Warne has 137 to 205 IPL balls per pressure group
    and Bumrah 363 to 767. Neither bowler's wicket rate rises smoothly with pressure.
    For example, Warne's medium-pressure rate is above his low-pressure rate, and
    Bumrah's is below. This is kept rather than forced into a pattern.
