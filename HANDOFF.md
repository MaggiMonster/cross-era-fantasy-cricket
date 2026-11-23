# HANDOFF

## Whose turn is it?

**Current turn: Turn 6 - Jaivin** (folder `~/cricket-project/project-friend`), still open.
Everything is built except the Bumrah and Warne photos, which Jaivin is downloading, and the faces.

The plan changed on 2026-11-23 to a 3D browser game in Three.js. The Bayesian networks,
match engine and Pygame game stay as a working fallback. The older video-generation
handoff is in `archive/docs/HANDOFF-old-scope.md`.

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Restructure, interface, Cricsheet parsing, batting networks | done (2026-11-23) |
| 2 | Jaivin | Bowling networks, combined outcome model | done (2026-11-23) |
| 3 | Apurva | Match engine, Pygame screen, batting controls, pace-vs-spin adjustment | done (2026-11-23) |
| 4 | Jaivin | Three.js scaffold, ball physics, JS sampler, capsule players, validation, asset research | done (2026-11-23) |
| 5 | Apurva | Character pipeline, Sachin and Kohli, eight batting shots, 3D batting controls | done (2026-11-23), faces pending |
| 6 | Jaivin | Bumrah and Warne, bowling actions and controls, auto mode, character select | **in progress**, photos and faces pending |
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

## Turn 5 - Apurva - done

- Blender 5.3 installed. `pipeline/build_batter.py` builds Sachin and Kohli with a rig, kit,
  pads, helmet, bat, an idle clip and all eight batting shots.
- The game loads them from `~/cricket-project/assets/`, which is **not in git**. Jaivin's
  folder shares those files. If they are missing, the game falls back to capsules.
- 3D batting controls: arrows, Shift plus arrows, and keys 1-8.
- **Tendulkar review: priors not changed.** He and Bumrah are both below the IPL average, so
  a matchup should fall below both. `docs/validation.md` now shows that expected value, and
  the reasoning is in `docs/assumptions.md`, items 41 to 43.
- **Leaving the ball now depends on line and length.** Leaving a straight full ball is high
  risk, a leave cannot score, and the rule is in `duel/matchup.py` and `web/src/model/duel.js`
  (`docs/assumptions.md`, items 46 to 50). Jaivin: this touches your Turn 2 matchup model.
- **Better batting animation.** Sachin and Kohli now use realistic MPFB bodies with a finger
  grip, a trigger movement, wrist and bat-face rotation, blending between clips, and a bat that
  is steered to the real ball. Watch it with `?closeup=1`.
- MPFB is installed in Blender on this Mac. Turn 6 can reuse `pipeline/build_batter.py`.
- **Camera and footwork.** The normal view starts wide and pushes in over the bowler's shoulder.
  The C key switches to the close view. Shots have front-foot and back-foot versions, and the
  planted foot no longer slides.
- **Photos are ready for both batters** in `~/cricket-project/assets/photos/tendulkar/` (8) and
  `kohli/` (7), with sources in `SOURCES.md`. Neither set has a true side profile, and most
  heads are under the 500-pixel target.
- Apurva reports the professor allows any photos for this private project. Keep photos, heads
  and any demo showing the faces out of public places.
- Schema is now `1.7` for the player API. No shared types changed.

## Turn 6 - Jaivin - in progress

- `pipeline/build_bowler.py` builds Bumrah and Warne on the MPFB pipeline, with scripted run-ups
  and deliveries. Their files are in `~/cricket-project/assets/`, not in git.
- **Human bowling:** keys 1-5 pick length, arrows pick line, Enter or Space bowls. The batting
  and outcome networks still decide every ball.
- **Auto mode** and a **start menu** with character select, mode, overs and lives. Portraits are
  rendered from the 3D heads, so they update when real faces arrive.
- Release heights now match the models' reach (`docs/assumptions.md`, items 57 to 60).
- A full one-over bowling duel was played with real key presses in headless Chrome.
- Schema is now `1.8` for the browser API. No shared types changed.

## Next: finish Turn 6 - Jaivin

1. Jaivin saves 6 to 8 photos each to `~/cricket-project/assets/photos/bumrah/` and `warne/`,
   following the checklist in `docs/asset-pipeline.md`, and logs each one in `SOURCES.md`.
2. With all four photo sets ready, install FaceBuilder, export one test head to `.glb`, then build
   all four inside the 15-day trial. Do not start the trial before then.
3. Close Turn 6 and hand over to Apurva for Turn 7.

## Blockers and open questions

- **Bowling actions need a person's judgement** at real speed on the Mac.
- **Faces are placeholders** until FaceBuilder is installed. Its glTF export and Blender 5.3
  support are not yet tested. The 15-day trial covers all four heads.
- **Shot quality still needs a person's judgement.** The blade reaches within 12 cm of the ball
  in 176 of 210 shot and delivery combinations. Poor shot choices can still visibly miss.
- **No animation pack is approved.** CGTrader and TurboSquid details could not be fully
  verified. Bought packs may not be allowed in a publicly deployed browser game.
- **Scripted shots** are technique-based keyframes, not motion capture of the real players.
- **Validation differences.** Tendulkar vs Bumrah is below both players' IPL rates, which is
  expected. Kohli vs Warne has dots below both, and its runs are 0.036 above expectation.
- **Bowler labels need a human check.** Tick the lists in `docs/validation.md`. Look closely
  at BAW Mendis, a mystery spinner labelled finger spin.
- **The 3D game was checked in headless Chrome** with software rendering and fixed time
  steps. Real-time feel and keyboard play on the Mac still need a person to try them.
- Ball direction after the bat is a placeholder until Turn 7.
- Small samples remain: Tendulkar's IPL high-pressure group is 94 balls, and Warne's IPL
  pressure groups are 137 to 205 balls. Warne's Cricsheet Tests cover only 2004-2007.
- Ignored files do not move with `git pull`. Old venvs or weights may remain in
  `project-friend/generation/` (`.venv` and `models`, 1.0 GB). Delete them only if you both agree.
