# Cross-Era Cricket Duel

Two-person university project. A 2D 1-vs-1 cricket game where famous batsmen and
bowlers are Bayesian networks learned from real data. Old era: Sachin Tendulkar,
Shane Warne. New era: Virat Kohli, Jasprit Bumrah. Matchups are always old vs new:
Sachin vs Bumrah, Kohli vs Warne.

## Game

The batsman chases a target over a set number of overs with a set number of lives
(default 3 overs, 3 lives, target from the player's real scoring rate; all
configurable). Each ball: the bowler's network samples a delivery (pace or spin,
length, line), the batsman's network samples a shot given the delivery and match
situation, and an outcome network gives dot, 1, 2, 3, 4, 6 or a wicket type.
Modes: human bats, human bowls, auto.

## Hard limits

- Python, pgmpy for the networks, Pygame for a simple 2D side-on view.
- Must run on one MacBook Air M4, 16 GB RAM, no GPU, shared by both contributors.

## Data rules

- Ball-by-ball data: Cricsheet (free, CC BY 4.0, always credit). It has runs,
  wickets and dismissal types but no line or length. We use Tests + IPL.
- Career aggregates go in `duel/data/career_stats.csv`, hand-entered, with a source
  for every number. Do not scrape sites whose terms forbid it.
- Anything not in the data is a documented prior, adjusted by the player's real
  stats. Write every assumption in `docs/assumptions.md`.
- These matchups never happened: document how batsman and bowler probabilities
  are combined.

## Contributors

| Person | GitHub       | Folder                             | Owns    |
|--------|--------------|------------------------------------|---------|
| Apurva | MaggiMonster | `~/cricket-project/project-me`     | Batsmen (Sachin, Kohli) |
| Jaivin | JaivinB      | `~/cricket-project/project-friend` | Bowlers (Bumrah, Warne) |

Both folders are clones of the same repo. Turns alternate, and the folder you are
running in decides who the current person is.

## Work packages

- **Turn 1 - Apurva:** repo restructure and docs; `docs/interface.md` (Delivery,
  Shot, Outcome, MatchState, network structure); shared Cricsheet download and
  parsing; batting networks for Sachin and Kohli, with tests.
- **Turn 2 - Jaivin:** bowling networks for Bumrah and Warne (pace vs leg-spin
  delivery distributions, wicket-taking tendencies); the combined per-ball outcome
  model for a matchup; tests.
- **Turn 3 - Apurva:** match engine (overs, lives, target, ball-by-ball sampling);
  Pygame screen with pitch, batsman sprite and shot animations, batting controls,
  scoreboard.
- **Turn 4 - Jaivin:** bowler run-up and ball path that depends on length and line,
  bowling controls, auto mode, matchup menu; validation that simulates 1000 duels
  per matchup and compares results to the players' real numbers, in
  `docs/validation.md`.

## Rules (apply to every session)

1. At the start of every session: run `pwd` and `git config user.name`, run
   `git pull`, then read CLAUDE.md and HANDOFF.md. HANDOFF.md says whose turn it
   is. If the person for this folder does not match whose turn it is, STOP and
   tell me to switch folders. Never change git config and never commit under the
   other person's identity.
2. Work only on the current turn's package. Do not start the next person's
   package, even if asked.
3. Commit in small, clear commits and run any tests before pushing.
4. Never add Claude attribution to commits or pull requests.
5. At the end of each turn: run tests, push all commits, update HANDOFF.md (what
   was done, what is next, blockers), commit and push that too. Then give a
   plain-language summary of what you changed so the current person can review
   it, and STOP with this exact message: "Turn complete. Next up: <Name>. Type
   /exit, then run: cd ~/cricket-project/<folder> && claude, then say 'continue'."

## Layout and commands

- `duel/types.py` - shared types. `docs/interface.md` is the contract; change them
  together and bump `SCHEMA_VERSION`.
- `duel/cricsheet.py` - download and parse. `duel/career.py` - career stats.
- `duel/batting.py` - batting networks.
- `archive/` - old video-generation scope; do not extend it.
- Run everything from the repo root, using the venv at `.venv`:
  - setup: `/opt/homebrew/bin/python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`
  - tests: `.venv/bin/python -m pytest tests -q`
  - rebuild data: `.venv/bin/python -m duel.cricsheet`
- Raw data, `outputs/` and venvs are git-ignored; never commit them.
