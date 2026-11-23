# HANDOFF

## Whose turn is it?

**Next turn: Turn 5 - Apurva** (folder `~/cricket-project/project-me`)

The plan changed on 2026-11-23 to a 3D browser game in Three.js. The Bayesian networks,
match engine and Pygame game stay as a working fallback. The older video-generation
handoff is in `archive/docs/HANDOFF-old-scope.md`.

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Restructure, interface, Cricsheet parsing, batting networks | done (2026-11-23) |
| 2 | Jaivin | Bowling networks, combined outcome model | done (2026-11-23) |
| 3 | Apurva | Match engine, Pygame screen, batting controls, pace-vs-spin adjustment | done (2026-11-23) |
| 4 | Jaivin | Three.js scaffold, ball physics, JS sampler, capsule players, validation, asset research | done (2026-11-23) |
| 5 | Apurva | Character pipeline, Sachin and Kohli, eight batting shots, 3D batting controls | **next** |
| 6 | Jaivin | Bumrah and Warne, bowling actions and controls, auto mode, character select | planned |
| 7 | Apurva | Shot direction and distance, fielders, replays, camera cuts, final docs, demo | planned |

## Earlier turns

- **Turn 1:** repo restructure, `docs/interface.md`, Cricsheet parsing, batting networks.
- **Turn 2:** bowling networks and the log5 matchup model.
- **Turn 3:** match engine, Pygame game, measured pace-vs-spin adjustment.

## Turn 4 - Jaivin - done

- `web/`: Three.js stadium, pitch, broadcast camera, lighting, capsule players with kit
  numbers, and a playable duel. Run `cd web && npm install && npm run dev`.
- `web/src/sim/ball.js`: 3D ball path from bowler, pace or spin, length and line.
- `duel/export_web.py` and `web/src/model/duel.js`: network tables in JSON, sampled in JS.
  `tests/test_web_sampler.py` shows every probability matches Python, and the same random
  numbers give identical duels.
- `duel/validate.py` and `docs/validation.md`: 1000 duels per matchup and the 20 most-faced
  bowlers for each batsman. Tendulkar beats Bumrah in 32.9% of duels, Kohli beats Warne
  in 33.9%.
- `docs/asset-pipeline.md`: motion and face research, source-independent pipeline, and
  DeepMotion click-through.
- Node.js was installed with Homebrew. `~/cricket-project/assets/` and `SOURCES.md` exist.
- Schema is now `1.3`, with no change to the shared types. 83 tests pass.

## Motion capture plan (decided 2026-11-23)

1. **Start with DeepMotion Animate 3D** to get working animations quickly. Apurva creates
   the account and uploads the clips personally. Steps are in `docs/asset-pipeline.md`.
2. **Keep the pipeline independent of the source.** Every tool's output goes to
   `raw/<source>/<action>/` and is retargeted to `animations/<source>/<action>.glb` on the
   same rig. The game code must not depend on which tool produced a file.
3. **Later, run the same master clips through ExMR** on Apurva's RTX 4060 (Windows, via
   WSL) and compare them side by side with DeepMotion on the same rig and camera.

## Next: Turn 5 - Apurva

1. Run `git pull`, then `cd web && npm install`.
2. Settle the two open decisions below.
3. Build the base rigged body, face method and kit, then Sachin and Kohli.
4. Capture the eight batting shots with DeepMotion and retarget them through the pipeline.
5. Add 3D batting controls. Replace the capsules in `web/src/scene/players.js`, keeping
   `root`, `reset` and `setSwing`.

## Blockers and open questions

- **Face method is undecided.** Recommendation: KeenTools FaceBuilder's 15-day free trial.
- **Clip source is undecided.** Open clips of Bumrah or Warne bowling and Tendulkar batting
  were not found, and there is only one short Kohli clip. Options: film ourselves
  (recommended), Creative Commons club clips, or both.
- **Blender is not installed.** Turn 5 needs it for rigging and retargeting.
- **DeepMotion limits.** The free tier gives 60 credits a month. Some button labels could
  not be confirmed. Its terms allow processing uploads to improve its services.
- **Validation differences.** Tendulkar vs Bumrah has runs and boundaries below both
  players' real IPL rates, and dots above both. Kohli vs Warne has dots below both. Line,
  length and shot choice are still priors, so these may need tuning.
- **Bowler labels need a human check.** Tick the lists in `docs/validation.md`. Look closely
  at BAW Mendis, a mystery spinner labelled finger spin.
- **The 3D game was checked in headless Chrome** with software rendering and fixed time
  steps. Real-time feel and keyboard play on the Mac still need a person to try them.
- Ball direction after the bat is a placeholder until Turn 7.
- Small samples remain: Tendulkar's IPL high-pressure group is 94 balls, and Warne's IPL
  pressure groups are 137 to 205 balls. Warne's Cricsheet Tests cover only 2004-2007.
- Ignored files do not move with `git pull`. Old venvs or weights may remain in
  `project-friend/generation/` (`.venv` and `models`, 1.0 GB). Delete them only if you both agree.
