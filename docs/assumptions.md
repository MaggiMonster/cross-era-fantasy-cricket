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
13. **Pace vs spin has two layers.** `SHOT_BY_BOWL` and `BOWL_EFFECT` are a shared
    **prior**. Each batter's own difference is measured, as described in the section
    "Pace vs spin adjustment".
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

15. **Baseline population** is every ball in the Cricsheet Tests + IPL archives,
    all batters and bowlers. It goes through the same smoothing, Test/IPL blend and
    batting tables as a player.
16. **The baseline depends on the delivery.** Both the batter's and the bowler's
    tables contain the same delivery effects (for example, yorkers hit the stumps
    more). Dividing by a delivery-specific baseline stops those effects being
    counted twice.
17. **Independence.** Log5 assumes batter and bowler deviations combine without
    interaction. A batter's general record against a bowling type is modelled (see
    "Pace vs spin adjustment"), but any effect specific to one bowler is not.
18. **Only two matchups are allowed:** Tendulkar vs Bumrah and Kohli vs Warne.

## Bowling network

19. **Structure** (`duel/bowling.py`): Pressure -> Length -> Line, and Pressure,
    Length, Line -> Outcome. Bowling type is fixed per bowler: Bumrah pace, Warne
    leg-spin, as listed on their Wikipedia profiles.
20. **No line or length data exists.** `LENGTH_PRIOR` and `LINE_PRIOR` are
    **priors**. Bumrah bowls more yorkers as pressure rises. Warne bowls fuller and
    uses the leg-side line more than Bumrah.
21. **Outcome rates are measured.** Each bowler's IPL rates by pressure use the same
    100-ball smoothing, `TEST_WEIGHT` and 50/50 dismissal mix as the batters. Risk is
    relative to the whole population, because a bowler faces all kinds of batter.
22. **Career correction.** Test wicket risk per ball is multiplied by (Cricsheet
    bowling average / career bowling average). Cricsheet has Bumrah's full Test
    record to date, but Warne's Tests only from 2004 to 2007.
23. **Run-outs stay in the outcome states** for the shared format, but they do not
    count as the bowler's wickets in the career correction. Byes and leg byes are not
    charged to the bowler.
24. **Small samples remain noisy.** Warne has 137 to 205 IPL balls per pressure group
    and Bumrah 363 to 767. Neither bowler's wicket rate rises smoothly with pressure.
    For example, Warne's medium-pressure rate is above his low-pressure rate, and
    Bumrah's is below. This is kept rather than forced into a pattern.

## Pace vs spin adjustment

Code: `duel/pace_spin.py`. Rebuild the counts with `python -m duel.pace_spin`.

Batting average (runs per dismissal, run-outs excluded) on the Cricsheet balls whose
bowler is labelled:

| Batter | Format | Pace | Finger spin | Wrist spin |
|--------|--------|------|-------------|------------|
| Tendulkar | Tests | 51.8 | 52.3 | 78.8 (6 outs) |
| Tendulkar | IPL | 38.9 | 40.5 | 39.2 (5 outs) |
| Kohli | Tests | 43.3 | 52.7 | 81.2 (10 outs) |
| Kohli | IPL | 36.2 | 62.6 | 53.6 (23 outs) |

25. **Bowler labels.** `duel/data/bowler_types.csv` labels 294 bowlers as pace, finger
    spin or wrist spin, covering 95.4% of Tendulkar's and 94.0% of Kohli's Cricsheet
    balls. Labels were hand-entered from general cricket knowledge and **have not been
    checked one by one** against a reference. Bowlers with a mixed or unclear style
    (for example Andrew Symonds) are left out.
26. **Leg-spin estimate.** Warne is the only spinner in the game, so a batter's spin
    rate is their wrist-spin record, backed by 500 pseudo-balls of their all-spin
    rate (**prior**), because the wrist-spin samples are small.
27. **Relative effect.** For wickets and boundaries, the spin-to-pace log ratio is
    computed by format, shrunk by events / (events + 20) (**prior**), weighted 50/50
    Tests and IPL, and compared with the two batsmen pooled. The shared difference
    between pace and spin stays in the prior tables.
28. **Result.** Tendulkar: wicket odds x0.92 against pace and x1.09 against spin.
    Kohli: x1.09 against pace and x0.92 against spin. Boundary odds move by under 2%.
    Multipliers are capped at x1.5 either way.
29. **The effects mirror each other.** With only two batsmen in the pool, one batter's
    relative strength is the other's relative weakness. This shows how they differ
    from each other, not how they compare with all batsmen.
30. **Size in a matchup.** Wicket risk per ball falls by about 7% (6.6% to 7.6%) in both real
    matchups, and runs per ball change by less than 0.5%. Calibration keeps each
    batter's overall rates over the 50/50 reference mix.
31. **The baseline has no player adjustment**, so log5 does not cancel it.
32. **Era is not modelled.** The counts pool each batter's Cricsheet career. Tendulkar's
    data starts in 2001, and Kohli's form changed after 2020.
33. **Published check.** Sidharth Monga, ESPN, 8 January 2025,
    <https://www.espn.co.uk/cricket/story/_/id/43330624/virat-kohli-weakness-stump>:
    Kohli averaged 62 from 2015 to 2019 and 14 since 2020 against length and
    short-of-length balls at third and fourth stump. This supports a vulnerability to
    seam outside off, but is not used as a model input. Other published pace/spin
    splits we found could not be opened and checked, so none are cited.

## Match engine

34. **Default target** is one more than the batter's IPL runs per ball times the balls
    available, rounded down: 22 for Tendulkar and 25 for Kohli over 3 overs.
35. **A wicket costs one life.** The batter's score carries on and the ball counts.
36. **The human sees the delivery before choosing a shot**, because the game has no
    real-time timing. Shot choice changes the outcome odds only through the model.

## 3D browser game

37. **The JS sampler is a port, not a new model.** It samples the exported tables with
    the same draw order and inverse-CDF rule as NumPy's `choice`. Given the same random
    numbers, it plays identical duels (`tests/test_web_sampler.py`).
38. **Ball physics is presentation only.** The networks decide the outcome first, then
    the ball is animated to fit it.
39. **Pitch distances, speeds, release points, swing, turn and bounce** in
    `web/src/sim/ball.js` are **priors** chosen to look plausible. Bumrah is about 142
    km/h and Warne about 81 km/h. None are measured from the players.
40. **Direction after the bat** was a placeholder until Turn 7. See items 61 to 70.

## Tendulkar scoring-rate review (Turn 5)

41. **His batting priors were reviewed and not changed.** The duel's 1.063 runs per ball
    looked too slow beside his real IPL 1.198, but that comparison ignores the opponent.
    Tendulkar (1.198) and Bumrah (1.166 conceded) are both below the IPL population
    average of 1.333, so a fair matchup should fall below both players.
42. **Evidence.** Log5 of the real rates alone, with no line, length or shot priors, at
    the duel's pressure mix gives 1.102 runs per ball. The model's exact expected value
    is 1.083, which is 0.019 lower, or about 0.3 runs over 18 balls. The 1000-duel sample
    reads 0.040 lower because it also includes random variation. Kohli vs Warne is 0.036
    above its expectation, so the priors do not lean one way against batters in general.
    Raising Tendulkar's rates to match 1.198 would make him better than his record.
43. **What changed.** `docs/validation.md` now shows the log5 expectation for each matchup.

## Character animation (Turn 5)

44. **Batting animations are hand-authored keyframes**, not motion capture of the real
    players. Poses in `pipeline/build_batter.py` are **priors** based on general batting
    technique. Sachin's compact stance and short backlift and Kohli's high backlift are
    stylised impressions and are not measured from footage.
45. **Animation is presentation only.** Controls and clips choose how a shot looks and
    never change the probabilities.

## Leaving the ball (Turn 5)

46. **Why this rule exists.** The batting outcome table has no line, so leaving a straight
    ball was as safe as leaving a wide one. Cricsheet has no line data to learn this from.
47. **Prior risk of bowled or lbw on a leave** (`LEAVE_RISK_BY_LINE` in `duel/matchup.py`):

    | Line | Yorker | Full | Good | Short | Bouncer |
    |------|--------|------|------|-------|---------|
    | Outside off | 1.5% | 1.2% | 1.0% | 0.7% | 0.2% |
    | Stumps | 35% | 30% | 18% | 6% | 0.5% |
    | Leg | 0.6% | 0.5% | 0.4% | 0.2% | 0.1% |

48. **Player adjustment.** The odds are multiplied by the batter's and bowler's wicket
    rates on that delivery relative to the baseline, limited to x0.5 to x2.
49. **A leave cannot score or be caught or run out.** Stumped keeps its log5 probability.
50. **Limitation.** Line is where the ball is heading in simple terms. A leg-break pitching
    on leg that turns to hit off is not modelled separately.

## Batting animation upgrade (Turn 5)

51. **Bodies are generic MPFB humans** shaped by a **prior** height and build for each player.
    They are not likenesses. Faces still need FaceBuilder.
52. **The bat is steered to the ball at run time** with footwork (up to 24 cm across the crease),
    the hands (up to 55 cm) and the wrists (up to 48 degrees). These limits are **priors**.
53. **Measured contact.** Over 7 shots, 15 deliveries and both matchups, the blade comes
    within 12 cm of the ball in 176 of 210 cases, with both hands kept on the handle. Most
    other cases are poor shot choices for the ball, and the worst gap is 49 cm.
54. **This is presentation only.** Steering never changes the probabilities.
55. **Footwork versions are chosen by length.** Short balls and bouncers use back-foot defend,
    work and drive. Yorkers and full balls use front-foot cut and pull. This is a **prior**.
56. **The planted foot stays still** during the swing (measured drift under 1 cm). The batter
    still resets to the stance between balls.

## Bowlers and human bowling (Turn 6)

57. **Bowler bodies and heads are generic MPFB humans** shaped by a **prior** height and build,
    with stylised hair, brows and beard. They are not likenesses and were not made from photos.
58. **Bowling actions are scripted keyframes**, stylised from general knowledge of each player.
    They are not motion capture or measurements.
59. **Release heights are set by the models' reach:** 2.08 m for Bumrah (was 2.12) and 2.11 m
    for Warne (was 1.86). This changes only the drawn ball path, never a probability.
60. **A human bowler replaces only the delivery sample.** Length and line are chosen by the
    player, and the batting and outcome networks then decide the ball as usual. A human can
    pick combinations the real bowler rarely bowled, so human-bowling results are not part of
    the 1000-duel validation.

## Shot direction, fielders, replays and cameras (Turn 7)

61. **The networks decide first, and the ball is then drawn to fit.** `web/src/sim/hit.js` uses
    only the visual random generator, so where the ball goes can never change a result.
62. **Each shot has an arc**, for example a cut to the off side square of the wicket and a pull to
    leg (`SECTORS`). The line nudges it by about 10 degrees towards off or leg. These arcs are
    **priors** from general cricket knowledge. Cricsheet does not record where the ball went.
63. **Distance comes from the outcome.** Roughly: dot up to 14 m, 1 run 16-30 m, 2 runs 34-48 m,
    3 runs 50-60 m, all kept at least 7 m inside the rope. These bands are **priors**.
64. **Boundaries find a gap.** A four runs along the ground to the rope, and a six lands 7.5 m
    beyond it. The game tries angles across the shot's arc and picks one that no fielder can
    reach in time, widening the arc if it has to. A test checks this for every shot and line.
65. **Fielders run at 7 m/s after a 0.25 s reaction.** Both are **priors** for a sprinting
    fielder. A catch is held by the fielder whose position best matches the shot. Edged shots
    (defend, drive, cut, work) are caught by the keeper or slip.
66. **Fields are fixed per bowling type,** not per bowler or match state. Pace has a slip, deep
    third and fine leg. Spin has a slip, deep cover and long-on. Both are **priors**.
67. **There is only one batter on screen,** so runs are not run between the wickets. A run out is
    shown as a throw that breaks the stumps.
68. **Replays** are shown after every four, six and wicket, slowed to 0.3x through the contact.
    Space, Enter or the replay button skips one, and `&replays=0` turns them off.
69. **Camera cuts** follow the ball from behind the batter, then cut to the rope for boundaries,
    to the catcher for catches, and to the stumps for run outs. They apply in the normal view.
    The close view stays where it is during live play.
70. **Fielders are generic MPFB people** in the bowler's team colours, built by
    `pipeline/build_fielder.py`. They are not real players and use no photos. If their file is
    missing, simple jointed figures stand in. The keeper wears white gloves.
71. **Fielder clips are scripted keyframes**, priors from general cricket technique: a ready
    stance, a keeper and slip crouch, a 16-frame run at 7 m/s, a two-handed catch and a scoop then
    overarm throw. The run clip is played at the fielder's real ground speed, so feet do not slide.
72. **Hands are pulled onto the ball at run time.** For a catch both palms close round the ball
    in the last 0.28 s, and the ball then stays between them. For a pickup the right hand reaches
    the ball, then carries it until the throw is released. A catch is taken 0.45 m in front of the
    body at chest height (1.3 m), and a fielder stops 0.55 m short of a ball he picks up.

## Leg technique (Turn 7)

73. **Knees point over the toes.** Every leg's IK now has a pole target carried by the foot, so
    knees no longer fold inwards. The pole angle is measured by bending each leg in Blender.
74. **The planted foot rolls onto its toes** as weight moves through a shot, pivoting on the ball
    of the foot so it does not slide. The heel angles per shot (`HEEL_LIFT` in
    `pipeline/build_batter.py`) are **priors**, for example 38 degrees at contact in a drive and
    60 at the finish. In the sweep the back knee goes down to the ground.
75. **Run-ups now run.** A running foot (faster than 3.6 m/s) is down for under a third of its
    cycle, rolls onto its toes, kicks the heel up behind (up to 0.36 m) and swings through with the
    knee driving forward. The body bobs and sits lower while running. Warne's slower walk-in
    lifts less. These shapes are **priors**. Release positions did not change.
