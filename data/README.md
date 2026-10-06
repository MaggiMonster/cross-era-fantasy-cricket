# data/

Local test footage. Everything in this folder except this file is git-ignored.

Do not put copyrighted broadcast footage here (CLAUDE.md rule 4).

## Placeholder clip

Until a proper clip is supplied, development uses this openly licensed clip.
It is a **placeholder**: an amateur match filmed from a distance, not the
close-up reference footage the project needs.

| | |
|---|---|
| Local path | `data/placeholder/amar_kala_batting_2025.webm` |
| Title | "Amar Kala Batting Video 2025" (a cover drive in a domestic match, Prayagraj) |
| Author | DrRevathi25 |
| Licence | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| Source | https://commons.wikimedia.org/wiki/File:Amar_Kala_Batting_Video_2025.webm |
| Format | 720x1280 (letterboxed), 24.93 fps, 47.8 s, VP9 |

Download it with:

```sh
mkdir -p data/placeholder
curl -L -A "cross-era-cricket-student-project" \
  -o data/placeholder/amar_kala_batting_2025.webm \
  https://upload.wikimedia.org/wikipedia/commons/3/32/Amar_Kala_Batting_Video_2025.webm
```

Pose files extracted from it carry `"placeholder": true` in their metadata.
