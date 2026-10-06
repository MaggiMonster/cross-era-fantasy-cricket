# HANDOFF

## Whose turn is it?

**Next turn: Turn 2 - Jaivin** (folder `~/cricket-project/project-friend`)

| Turn | Person | Package | Status |
|------|--------|---------|--------|
| 1 | Apurva | Scaffolding, interface spec, core of `pose/` | done (2026-10-06) |
| 2 | Jaivin | `generation/` environment, model choice, smoke test | **next** |
| 3 | Apurva | Finish Milestone 1 | waiting |
| 4 | Jaivin | Finish Milestone 2 | waiting |

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

## Next: Turn 2 - Jaivin

Package, from `CLAUDE.md`:

- Set up `generation/` (its own venv at `generation/.venv`, `requirements.txt`).
- Verify PyTorch MPS works.
- Choose a pre-trained open-source image-to-video model that realistically runs
  in 16 GB on Apple Silicon (the proposal suggests LTX-2 or MagicAnimate; check
  what actually runs, quantized or reduced variant if needed).
- Download weights into an ignored folder and run a tiny smoke test, logging
  memory use.

Things worth knowing:

- This Mac has only the system Python 3.9.6 (`/usr/bin/python3`); no Homebrew
  Python, no `uv`. Recent PyTorch / diffusers releases may need a newer Python,
  so installing one is probably the first step.
- `.gitignore` already covers `models/`, `weights/`, `checkpoints/`, `.cache/`,
  `*.safetensors`, `*.ckpt`, `*.pt`, `*.pth`, `*.bin`, `*.gguf`, `outputs/` and
  any `.venv/`.
- `generation/` can read pose files with plain NumPy; see "Reading a file" in
  `docs/interface.md`. Pose conditioning itself is Milestone 3, not Turn 2.
- `ffmpeg` is installed at `/opt/homebrew/bin/ffmpeg`.

## After that: Turn 3 - Apurva

Normalize and smooth pose sequences, skeleton-overlay video, crop to the player,
isolate the delivery stride / action segment, more tests and docs.

## Blockers and open questions

- **No real test clip yet.** The placeholder is a distant amateur shot with
  several players in frame. Turn 3 needs closer clips of a cover drive, a
  fast-bowling delivery and a leg-spin delivery that we are allowed to use
  (self-filmed or openly licensed). No copyrighted broadcast footage.
- `mediapipe` is pinned to 0.10.21 because 1.0.1 crashes on this Mac
  (`pose/README.md`, "Version pin").
- The proposal mentions three students and an NVIDIA GPU; we are two people on
  one Apple Silicon Mac, so Part 3 (era filters, evaluation) is unassigned.
- `setup-test-apurva.txt` and `setup-test-jaivin.txt` are leftovers from the
  repo setup and can be deleted once both of us agree.
