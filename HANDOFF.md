# HANDOFF

## Whose turn is it?

**Next turn: Turn 3 - Apurva** (folder `~/cricket-project/project-me`)

The project changed scope to Cross-Era Cricket Duel on 2026-11-23, and turn numbers
restarted. The old Turn 4 (video generation) is cancelled. The old handoff is in
`archive/docs/HANDOFF-old-scope.md`.

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Restructure, interface, Cricsheet parsing, batting networks | done (2026-11-23) |
| 2 | Jaivin | Bowling networks, combined outcome model | done (2026-11-23) |
| 3 | Apurva | Match engine, Pygame screen, batting controls | **next** |
| 4 | Jaivin | Bowling view and controls, auto mode, menu, validation | not started |

## Turn 1 - Apurva - done

- Old code and docs moved to `archive/`. README, CLAUDE.md and this file rewritten.
- `docs/interface.md` and `duel/types.py`: the shared types and network structure.
- `duel/cricsheet.py`: downloads Tests + IPL and parses every ball.
  `data/cricsheet/balls.csv.gz` (git-ignored) holds all four players' balls.
- `duel/data/career_stats.csv`: sourced Test figures for the two batsmen.
- `duel/batting.py`: pgmpy networks for Tendulkar and Kohli.
- `docs/assumptions.md`: every prior and modelling choice so far.

## Turn 2 - Jaivin - done

- `duel/bowling.py`: pgmpy networks for Bumrah (pace) and Warne (leg-spin), with
  delivery choice by pressure and wicket tendencies from their real data.
- `duel/matchup.py`: `load_matchup(batter, bowler)` combines both players with log5.
  The baseline is all Tests + IPL balls, computed for each specific delivery.
- `duel/cricsheet.py` also writes `duel/data/bowling_counts.json`. The batting counts
  did not change.
- `duel/data/career_stats.csv`: sourced Test figures for both bowlers.
- `docs/interface.md` has the bowling and matchup API. Schema is now `1.1`, with no
  change to the shared types.
- 45 tests pass.

## Next: Turn 3 - Apurva

1. Run `git pull`. The `.venv` setup in CLAUDE.md is unchanged.
2. Build the match engine: overs, lives, target and ball-by-ball sampling. One ball
   is the code block under "Matchup model" in `docs/interface.md`.
3. Build the Pygame screen with pitch, batsman sprite, shot animations, batting
   controls and scoreboard.
4. Choose how the default target is set from the player's real scoring rate.

## Blockers and open questions

- No blockers.
- **Pace vs spin is a prior.** Cricsheet does not label bowling type. Hand-labelling
  the main bowlers faced would let us measure it.
- **Line, length and shot choice are priors**, for both batters and bowlers, so they
  need checking in the Turn 4 validation.
- **Small samples.** Tendulkar's IPL high-pressure group is 94 balls, and Warne's IPL
  pressure groups are 137 to 205 balls. Wicket risk does not rise smoothly with
  pressure for either bowler, and Turn 4 should check the effect on results.
- **Warne's Cricsheet Tests cover only 2004-2007.** They are corrected to his career
  bowling average, but his earlier peak is otherwise missing.
- The matchup model has passed unit tests and a per-ball sanity check only. The
  1000-duel validation is Turn 4.
- Importing pgmpy took about 20 seconds the first time on this Mac and is quicker
  afterwards. Turn 3 should load the networks before the game screen appears.
- Ignored files do not move with `git pull`. Old venvs or weights may remain in
  `project-friend/generation/` (`.venv` and `models`, 1.0 GB). Delete them only if you both agree.
