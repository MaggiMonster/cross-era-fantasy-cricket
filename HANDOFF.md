# HANDOFF

## Whose turn is it?

**Next turn: Turn 3 - Apurva** (folder `~/cricket-project/project-me`)

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Scaffolding, interface spec, core of `pose/` | done (2026-10-06) |
| 2 | Jaivin | `generation/` environment, model choice, smoke test | partly done (2026-10-06), rest deferred to Turn 4 |
| 3 | Apurva | Finish Milestone 1 | **next** |
| 4 | Jaivin | Finish Milestone 2 | waiting |

**Milestone 2 is partially done and deferred.** Full write-up:
`docs/m2-status.md`.

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

## Next: Turn 3 - Apurva

Normalize and smooth pose sequences, skeleton-overlay video, crop to the player,
isolate the delivery stride / action segment, more tests and docs.

Unaffected by the Milestone 2 problems; `generation/` does not read pose files yet.

## After that: Turn 4 - Jaivin

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
  several players in frame. Turn 3 needs closer clips of a cover drive, a
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
