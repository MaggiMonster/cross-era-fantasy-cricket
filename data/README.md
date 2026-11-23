# data/

Everything here except this file is git-ignored. Rebuild it from the repo root:

```sh
.venv/bin/python -m duel.cricsheet
```

This downloads the Test and IPL archives to `data/cricsheet/`, writes the four
players' balls to `data/cricsheet/balls.csv.gz`, and refreshes the committed
aggregates `duel/data/batting_counts.json` and `duel/data/bowling_counts.json`.
The bowling file also holds outcome counts for all balls, used as the baseline.

## Credit

Ball-by-ball data is from [Cricsheet](https://cricsheet.org), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). We changed it by
filtering to four players, mapping outcomes and aggregating counts. Cricsheet
does not endorse this project.
