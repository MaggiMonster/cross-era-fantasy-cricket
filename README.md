# Cross-Era Fantasy Cricket

Generate short clips of historical cricketers performing actions captured from
modern players: "what would Bradman look like facing a modern fast bowler?"

University project by Apurva Verma (MaggiMonster) and Jaivin (JaivinB).
The full proposal is in [`docs/proposal.docx`](docs/proposal.docx).

## Pipeline

1. **Motion extraction** (`pose/`) - pose estimation on a modern cricket clip
   gives a per-frame joint sequence.
2. **Image-to-video generation** (`generation/`) - a pre-trained open-source
   diffusion model animates a still image of a historical player along that motion.
3. **Era styling** (`era_filters/`) - grain, grading and frame-rate changes to
   match 1930s film or 1970s television.
4. **Evaluation** (`evaluation/`) - temporal smoothness and motion fidelity.

Stages 1 and 2 talk to each other only through the pose-sequence file described
in [`docs/interface.md`](docs/interface.md).

## Constraints

- One MacBook Air M4, 16 GB RAM, Apple Silicon (PyTorch MPS, no CUDA).
- 512x512, 3-5 second clips (60-100 frames).
- Pre-trained weights only; LoRA / adapters, no training from scratch.

## Milestones

| # | Goal | Status |
|---|------|--------|
| 1 | Motion extraction toolkit, delivery stride isolated | in progress |
| 2 | Image-to-video model running locally without OOM | not started |
| 3 | Pose-conditioned generation via control adapters | not started |
| 4 | Era filters, evaluation, final catalog | not started |

## Quick start (pose extraction)

```sh
python3 -m venv pose/.venv
pose/.venv/bin/pip install -r pose/requirements.txt
pose/.venv/bin/python -m pose.extract path/to/clip.mp4 --action cover_drive
pose/.venv/bin/python -m pytest tests -q
```

See [`pose/README.md`](pose/README.md) for details and
[`data/README.md`](data/README.md) for the placeholder test clip.

## Working on this repo

Work alternates between the two contributors in turns. [`HANDOFF.md`](HANDOFF.md)
says whose turn it is and what is next; [`CLAUDE.md`](CLAUDE.md) holds the rules.
Model weights, videos, outputs and virtual environments are git-ignored.
