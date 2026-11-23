# HANDOFF

## Whose turn is it?

**Next turn: Turn 2 - Jaivin** (folder `~/cricket-project/project-friend`)

The project changed scope to Cross-Era Cricket Duel on 2026-11-23, and turn numbers
restarted. The old Turn 4 (video generation) is cancelled. The old handoff is in
`archive/docs/HANDOFF-old-scope.md`.

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Restructure, interface, Cricsheet parsing, batting networks | done (2026-11-23) |
| 2 | Jaivin | Bowling networks, combined outcome model | **next** |
| 3 | Apurva | Match engine, Pygame screen, batting controls | not started |
| 4 | Jaivin | Bowling view and controls, auto mode, menu, validation | not started |

## Turn 1 - Apurva - done

- Old code and docs moved to `archive/`. README, CLAUDE.md and this file rewritten.
- `docs/interface.md` and `duel/types.py`: the shared types and network structure.
- `duel/cricsheet.py`: downloads Tests + IPL and parses every ball.
  `data/cricsheet/balls.csv.gz` (git-ignored) holds all four players' balls,
  including Bumrah's and Warne's bowling.
- `duel/data/career_stats.csv`: sourced Test figures for the two batsmen.
- `duel/batting.py`: pgmpy networks for Tendulkar and Kohli.
- `docs/assumptions.md`: every prior and modelling choice so far.
- 19 tests pass.

## Next: Turn 2 - Jaivin

1. Recreate the environment: see "Layout and commands" in CLAUDE.md, then run
   `.venv/bin/python -m duel.cricsheet`.
2. Build `duel/bowling.py` to the contract in `docs/interface.md`.
3. Add Bumrah's and Warne's sourced career figures to `duel/data/career_stats.csv`.
4. Build the matchup outcome model using the method in `docs/assumptions.md`.
   Choose and document its `baseline`.
5. Add tests and record new assumptions.

## Blockers and open questions

- No blockers.
- **Pace vs spin is a prior.** Cricsheet does not label bowling type. Hand-labelling
  the main bowlers faced would let us measure it.
- **Line, length and shot choice are priors**, so they need checking in the Turn 4
  validation.
- Tendulkar's IPL high-pressure sample is only 94 balls and is heavily smoothed.
- Importing pgmpy took about 20 seconds the first time on this Mac and is quicker
  afterwards. Turn 3 should load the networks before the game screen appears.
- Ignored files do not move with `git pull`. Old venvs or weights may remain in
  `project-friend/generation/` (`.venv` and `models`, 1.0 GB). Delete them only if you both agree.
