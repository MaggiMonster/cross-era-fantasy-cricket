# data/

`data/cricsheet/balls.csv.gz` (about 200 KB) is committed. It holds every legal ball
faced by Tendulkar or Kohli or bowled by Bumrah or Warne, from the Cricsheet archives
downloaded on 2026-11-23. With it, the tests and `python -m duel.validate` reproduce the
report's numbers exactly, with no download. Everything else here is git-ignored.

To rebuild from the latest Cricsheet data, run from the repo root:

```sh
.venv/bin/python -m duel.cricsheet
```

This downloads the Test and IPL archives to `data/cricsheet/`, rewrites
`data/cricsheet/balls.csv.gz`, and refreshes the committed aggregates
`duel/data/batting_counts.json` and `duel/data/bowling_counts.json`. The bowling file also
holds outcome counts for all balls, used as the baseline.

**Rebuilding changes results.** Cricsheet keeps adding matches. A download after
2026-11-23 includes newer Bumrah Tests, which changes his counts. Some tests then fail until
`duel/data/career_stats.csv` is updated and `python -m duel.export_web` is rerun, and a few
validation numbers move by about 0.01.

## Credit

Ball-by-ball data is from [Cricsheet](https://cricsheet.org), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). We changed it by
filtering to four players, mapping outcomes and aggregating counts. Cricsheet
does not endorse this project.
