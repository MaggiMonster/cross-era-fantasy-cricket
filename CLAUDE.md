# Cross-Era Fantasy Cricket

Two-person university project. Pipeline: extract motion from modern cricket videos
(pose estimation), transfer it onto a static image of a historical player with a
pre-trained open-source image-to-video diffusion model, then apply era-specific
film styling. Full proposal: `docs/proposal.docx`.

## Hard limits

- 512x512 output, 3-5 second clips (60-100 frames).
- No training from scratch. LoRA / adapters only.
- Hardware: one MacBook Air M4, 16 GB RAM, Apple Silicon (PyTorch MPS, no CUDA),
  shared by both contributors.

## Contributors

| Person | GitHub       | Folder                            |
|--------|--------------|-----------------------------------|
| Apurva | MaggiMonster | `~/cricket-project/project-me`     |
| Jaivin | JaivinB      | `~/cricket-project/project-friend` |

Both folders are clones of the same repo. Turns alternate, and the folder you are
running in decides who the current person is.

## Work packages

- **Turn 1 - Apurva:** repo scaffolding (CLAUDE.md, README, .gitignore, HANDOFF.md,
  folders), `docs/interface.md` (pose-sequence format), core of `pose/` (video ->
  per-frame joints in that format).
- **Turn 2 - Jaivin:** `generation/` environment (venv, requirements), verify
  PyTorch MPS, choose a pre-trained open-source image-to-video model that runs in
  16 GB on Apple Silicon (quantized/reduced variant if needed), download weights
  into an ignored folder, run a tiny smoke test with memory logging.
- **Turn 3 - Apurva:** finish Milestone 1: normalize and smooth pose sequences,
  skeleton-overlay video, isolate the delivery stride / action segment, tests, docs.
- **Turn 4 - Jaivin:** finish Milestone 2: image-to-video at 512x512 for 3-5 s with
  memory logging and no OOM, document fallbacks (fewer frames, lower resolution,
  offloading), Colab/Kaggle notebook for heavier runs, results in `docs/m2-results.md`.
- **After Turn 4:** summarize both milestones and propose the plan for Milestone 3.

## Rules (apply to every session)

1. At the start of every session: run `pwd` and `git config user.name`, run
   `git pull`, then read CLAUDE.md and HANDOFF.md. HANDOFF.md says whose turn it
   is. If the person for this folder does not match whose turn it is, STOP and
   tell me to switch folders. Never change git config and never commit under the
   other person's identity.
2. Work only on the current turn's package. Do not start the next person's
   package, even if asked.
3. Commit in small, clear commits and run any tests before pushing.
4. For test video: if I have not supplied a clip, ask me for one, or use a
   synthetic or openly licensed clip clearly labeled as a placeholder. Do not
   download copyrighted broadcast footage.
5. At the end of each turn: run tests, push all commits, update HANDOFF.md (what
   was done, what is next, blockers), commit and push that too. Then give a
   plain-language summary of what you changed so the current person can review
   it, and STOP with this exact message: "Turn complete. Next up: <Name>. Type
   /exit, then run: cd ~/cricket-project/<folder> && claude, then say 'continue'."

## Layout and commands

- `pose/` - Part 1, motion extraction. Own venv at `pose/.venv` (`pose/README.md`).
- `generation/` - Part 2, image-to-video. Own venv at `generation/.venv`.
- `era_filters/`, `evaluation/` - later milestones.
- `docs/interface.md` - the contract between `pose/` and `generation/`. Change it
  only together with `pose/format.py` and bump `schema_version`.
- Run everything from the repo root:
  - tests: `pose/.venv/bin/python -m pytest tests -q`
  - extract: `pose/.venv/bin/python -m pose.extract <video> --action <label>`
- Weights, videos, `outputs/` and venvs are git-ignored; never commit them.
