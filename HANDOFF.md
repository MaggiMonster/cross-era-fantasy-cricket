# HANDOFF

## Whose turn is it?

**Next turn: Turn 4 - Jaivin** (folder `~/cricket-project/project-friend`)

The project changed scope to Cross-Era Cricket Duel on 2026-11-23, and turn numbers
restarted. The old Turn 4 (video generation) is cancelled. The old handoff is in
`archive/docs/HANDOFF-old-scope.md`.

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Restructure, interface, Cricsheet parsing, batting networks | done (2026-11-23) |
| 2 | Jaivin | Bowling networks, combined outcome model | done (2026-11-23) |
| 3 | Apurva | Match engine, Pygame screen, batting controls, pace-vs-spin adjustment | done (2026-11-23) |
| 4 | Jaivin | Bowling view and controls, auto mode, menu, validation | **next** |

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

## Turn 3 - Apurva - done

- `duel/engine.py`: overs, lives, target and ball-by-ball sampling. Default targets
  over 3 overs are 22 (Tendulkar) and 25 (Kohli).
- `duel/game.py`: Pygame screen with pitch, batsman, eight shot animations, keys `1`
  to `8`, and a scoreboard. Choose the matchup with `--matchup`.
- `duel/pace_spin.py`: measured pace-vs-spin adjustment for both batsmen, using 294
  labelled bowlers in `duel/data/bowler_types.csv`. Method and sources are in
  `docs/assumptions.md`.
- `requirements.txt` adds `pygame-ce`. Schema is now `1.2`, with no change to the
  shared types.
- 76 tests pass. The screen was tested without a real window and from saved images.

## Next: Turn 4 - Jaivin

1. Run `git pull`, then `.venv/bin/pip install -r requirements.txt` for Pygame.
2. Add the bowler run-up and a ball path that depends on length and line. `duel/game.py`
   has only a simple placeholder ball.
3. Add bowling controls, auto mode and the matchup menu. `Duel.play(shot=None)` already
   lets the network choose the shot.
4. Simulate 1000 duels per matchup and compare with real numbers in `docs/validation.md`.

## Blockers and open questions

- No blockers.
- **Bowler labels are unchecked.** The 294 pace/spin labels come from general cricket
  knowledge and need a spot check.
- **The pace-vs-spin effect is small and relative.** It changes wicket risk by 5% to 7%
  in the real matchups and barely changes runs. With two batsmen, their effects mirror
  each other.
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
  afterwards. `duel/game.py` loads the networks before opening the window.
- Ignored files do not move with `git pull`. Old venvs or weights may remain in
  `project-friend/generation/` (`.venv` and `models`, 1.0 GB). Delete them only if you both agree.
