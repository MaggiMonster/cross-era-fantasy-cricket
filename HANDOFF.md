# HANDOFF

## Whose turn is it?

**Current turn: Turn 5 - Apurva, still in progress** (folder `~/cricket-project/project-me`).
It is waiting on Apurva for face photos and a decision on animation packs.

The plan changed on 2026-11-23 to a 3D browser game in Three.js. The Bayesian networks,
match engine and Pygame game stay as a working fallback. The older video-generation
handoff is in `archive/docs/HANDOFF-old-scope.md`.

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Restructure, interface, Cricsheet parsing, batting networks | done (2026-11-23) |
| 2 | Jaivin | Bowling networks, combined outcome model | done (2026-11-23) |
| 3 | Apurva | Match engine, Pygame screen, batting controls, pace-vs-spin adjustment | done (2026-11-23) |
| 4 | Jaivin | Three.js scaffold, ball physics, JS sampler, capsule players, validation, asset research | done (2026-11-23) |
| 5 | Apurva | Character pipeline, Sachin and Kohli, eight batting shots, 3D batting controls | **in progress** (faces remain) |
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

## Motion and face plan (decided 2026-11-23)

**DeepMotion and ExMR are no longer the main plan.** We will not film ourselves or use
copyrighted match footage.

1. **Faces:** KeenTools FaceBuilder. The photo checklist is in `docs/asset-pipeline.md`.
2. **Motion:** a ready-made cricket pack if Apurva approves one, otherwise scripted Blender
   keyframes. Mixamo may supply generic running. Nothing is bought without asking.
3. **Signature touches** for all four players are in `docs/asset-pipeline.md`.

## Turn 5 - Apurva - done so far

- Blender 5.3 installed. `pipeline/build_batter.py` builds Sachin and Kohli with a rig, kit,
  pads, helmet, bat, an idle clip and all eight batting shots.
- The game loads them from `~/cricket-project/assets/`, which is **not in git**. Jaivin's
  folder shares those files. If they are missing, the game falls back to capsules.
- 3D batting controls: arrows, Shift plus arrows, and keys 1-8.
- **Tendulkar review: priors not changed.** He and Bumrah are both below the IPL average, so
  a matchup should fall below both. `docs/validation.md` now shows that expected value, and
  the reasoning is in `docs/assumptions.md`, items 41 to 43.
- Schema is now `1.4` for the player API change. No shared types changed.

## Next: finish Turn 5 - Apurva

1. Collect 6 to 8 photos each for Sachin and Kohli, using the checklist.
2. Install FaceBuilder, export one test head to `.glb`, then build both heads.
3. Decide whether to buy an animation pack. Check its shot list and licence first.
4. Play on the Mac and judge the feel of the shots.

Turn 6 (Jaivin) then builds Bumrah and Warne from the signature specs.

## Blockers and open questions

- **Faces are placeholders** until FaceBuilder is installed. Its glTF export and Blender 5.3
  support are not yet tested. The 15-day trial covers all four heads.
- **No animation pack is approved.** CGTrader and TurboSquid details could not be fully
  verified. Bought packs may not be allowed in a publicly deployed browser game.
- **Scripted shots** are technique-based keyframes, not motion capture of the real players.
- **Validation differences.** Tendulkar vs Bumrah is below both players' IPL rates, which is
  expected. Kohli vs Warne has dots below both, and its runs are 0.037 above expectation.
- **Bowler labels need a human check.** Tick the lists in `docs/validation.md`. Look closely
  at BAW Mendis, a mystery spinner labelled finger spin.
- **The 3D game was checked in headless Chrome** with software rendering and fixed time
  steps. Real-time feel and keyboard play on the Mac still need a person to try them.
- Ball direction after the bat is a placeholder until Turn 7.
- Small samples remain: Tendulkar's IPL high-pressure group is 94 balls, and Warne's IPL
  pressure groups are 137 to 205 balls. Warne's Cricsheet Tests cover only 2004-2007.
- Ignored files do not move with `git pull`. Old venvs or weights may remain in
  `project-friend/generation/` (`.venv` and `models`, 1.0 GB). Delete them only if you both agree.
