# HANDOFF

## Whose turn is it?

**Next turn: Turn 4 - Jaivin** (folder `~/cricket-project/project-friend`)

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Scaffolding, interface spec, core of `pose/` | done (2026-10-06) |
| 2 | Jaivin | `generation/` environment, model choice, smoke test | partly done (2026-10-06), rest deferred to Turn 4 |
| 3 | Apurva | Finish Milestone 1 | partly done (2026-10-06), rest listed below |
| 4 | Jaivin | Finish Milestone 2 | **next** |

**Milestone 1 and Milestone 2 are both partially done.** Turn 3 was cut short
for the presentation. Milestone 2 write-up: `docs/m2-status.md`.

## Turn 1 - Apurva - done

- Repo scaffolding: `CLAUDE.md` (rules), `README.md`, `.gitignore`, this file,
  folders `pose/ generation/ era_filters/ evaluation/ docs/ tests/ data/`.
- `docs/proposal.docx` committed.
- `docs/interface.md`: pose-sequence format, schema 1.0. One `.npz` per clip
  with `keypoints (T,33,3)`, `world (T,33,3)`, `visibility`, `detected`,
  `frame_index`, `timestamps` and a JSON `meta`.
- `pose/`: `python -m pose.extract <video>` reads a video, runs MediaPipe Pose
  Landmarker and writes that format. Reasons for choosing MediaPipe are in
  `pose/README.md`.
- 15 tests in `tests/`, all passing.
- Checked end to end on an openly licensed placeholder clip (`data/README.md`):
  person found in 154 of the first 200 frames, joints land on the batter.

## Turn 2 - Jaivin - partly done, stopped early for the presentation

Done:

- Python 3.12 installed with Homebrew (`/opt/homebrew/bin/python3.12`).
  `generation/.venv`, pinned `generation/requirements.txt`.
- PyTorch MPS verified, including half precision (`generation.check_env`).
- Model chosen: AnimateDiff v3 + SparseCtrl RGB on Stable Diffusion 1.5 via
  `diffusers` (reasons in `generation/README.md`). Weights, 4.6 GB, in the
  git-ignored `generation/models/`.
- Smoke test with memory logging (`generation.smoke_test`), component check
  (`generation.check_components`), 7 tests in `tests/test_generation_memlog.py`.

Not done:

- No usable clip yet. With 8 frames, frame 0 matches the input and the rest are
  abstract patterns. With 16 frames the clip is coherent but took 16 minutes
  while swapping, a repeat ran out of memory, and the clip does not keep the
  input image's look.
- Nothing above 256x256 has been run.

## Turn 3 - Apurva - partly done, cut short for the presentation

Done:

- `pose/overlay.py`: `python -m pose.overlay <video> <pose file>` draws joints
  and limbs on the source video and writes an H.264 `.mp4`, optionally cropped
  to the player (`--crop`), limited to a time range (`--start/--end`) and with
  one still PNG (`--still`). Options in `pose/README.md`.
- `pose/smooth.py`: centered moving average over the joint positions, recorded
  in `meta.processing`. Undetected frames stay `NaN`. On the placeholder a
  5-frame window cuts jitter from 6.0 to 1.4 pixels.
- 8 new tests in `tests/test_pose_overlay.py`; 23 pass under `pose/.venv`.
- Local, git-ignored outputs in `outputs/overlay/` (regenerate with the command
  in `pose/README.md`):
  - `amar_kala_batting_2025_skeleton_crop.mp4` - 2 s, 720x720, cropped to the batter.
  - `amar_kala_batting_2025_skeleton_crop.png` - still of frame 104, for a slide.
  - `amar_kala_batting_2025_skeleton_full.mp4` - the full 8 s, uncropped.

Seen in the overlay (detail in `pose/README.md`, "Measured on the placeholder
clip"): the 8 s contain two camera cuts, the skeleton is on the wrong person or
stretched between two people before frame 60, and the batter is only about 120
pixels tall. The cropped video starts at frame 60 for that reason.

Not done (next steps for Milestone 1, Apurva's next turn):

1. **Find real clips**: close shots of a cover drive, a fast-bowling delivery
   and a leg-spin delivery that we may use (self-filmed or openly licensed).
2. **Isolate the delivery stride / action segment** automatically. The time
   range for the overlay was picked by hand.
3. **Crop to the player before extraction**, so MediaPipe sees a large player
   and cannot jump to someone else. `overlay.player_box` only crops the picture
   after the fact.
4. **Normalize** pose sequences (centre and scale the player to the 512x512
   frame) and **resample** to the 60-100 frames the generator wants.
5. Better smoothing: split at camera cuts, and use a speed-adaptive filter so
   the bat swing is not rounded off.
6. A command that writes the smoothed pose file (smoothing is currently only
   applied inside the overlay or from Python).

## Next: Turn 4 - Jaivin

Finish Milestone 2, starting with the deferred items (detail in
`docs/m2-status.md`, "Next steps"):

1. Rerun 16 frames with `--attention-slicing` and other apps closed; record a
   clean time and memory peak.
2. Confirm the cause of the broken short clips (16 frames at 8 steps, 8 frames
   at 20 steps).
3. Try a real, openly licensed player photograph as input and check the clip
   keeps its appearance.
4. Go to 384 then 512 pixels; add CPU offloading or chunked decoding if needed.
5. Add `--device` to the smoke test and make a Colab/Kaggle notebook for the
   512x512, 3-5 second runs.
6. Make the smoke test's checks fail on a broken clip.
7. Results in `docs/m2-results.md`.

## Blockers and open questions

- **No real test clip yet.** The placeholder is a distant amateur shot with
  several players in frame, and the overlay shows the tracking is unreliable on
  it. Milestone 1 needs closer clips of a cover drive, a
  fast-bowling delivery and a leg-spin delivery that we are allowed to use
  (self-filmed or openly licensed). No copyrighted broadcast footage.
- `mediapipe` is pinned to 0.10.21 because 1.0.1 crashes on this Mac
  (`pose/README.md`, "Version pin").
- The proposal mentions three students and an NVIDIA GPU; we are two people on
  one Apple Silicon Mac, so Part 3 (era filters, evaluation) is unassigned.
- **Milestone 2 has no usable output yet** and 16 frames at 256x256 is already
  at the memory limit of the MacBook. 512x512 for 3-5 seconds will probably
  need Colab/Kaggle.
- The tests in `tests/test_generation_memlog.py` are skipped under `pose/.venv`
  (no psutil there). Run them with `generation/.venv/bin/python -m pytest`.
- The AnimateDiff repositories on Hugging Face declare no licence.
- `setup-test-apurva.txt` and `setup-test-jaivin.txt` are leftovers from the
  repo setup and can be deleted once both of us agree.
