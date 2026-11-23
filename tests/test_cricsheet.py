from duel.career import load_career_stats
from duel.cricsheet import batter_outcome, batting_counts, overs_to_balls, parse_match
from duel.types import MatchState, OutcomeType, Pressure


def ball(batter="V Kohli", runs=0, extras=None, wickets=None):
    total = runs + sum((extras or {}).values())
    b = {"batter": batter, "bowler": "X", "non_striker": "Y", "runs": {"batter": runs, "extras": total - runs, "total": total}}
    if extras:
        b["extras"] = extras
    if wickets:
        b["wickets"] = wickets
    return b


def match(deliveries, target=None, **innings):
    inn = {"team": "A", "overs": [{"over": 0, "deliveries": deliveries}], **innings}
    if target:
        inn["target"] = target
    return {"info": {"dates": ["2020-01-01"]}, "innings": [inn]}


def test_overs_notation():
    assert overs_to_balls(20) == 120
    assert overs_to_balls(19.3) == 117


def test_required_rate_ignores_wides_for_balls_but_counts_their_runs():
    rows = list(parse_match(match([ball(extras={"wides": 1}), ball(runs=4)], {"runs": 13, "overs": 2}), "m", "ipl"))
    assert rows[0]["required_rate"] == 6.5
    assert rows[1]["required_rate"] == 6.0


def test_super_over_skipped():
    assert list(parse_match(match([ball()], super_over=True), "m", "ipl")) == []


def test_outcomes():
    rows = list(parse_match(match([
        ball(extras={"wides": 1}),
        ball(extras={"legbyes": 1}),
        ball(runs=5),
        ball(wickets=[{"player_out": "V Kohli", "kind": "caught and bowled"}]),
        ball(wickets=[{"player_out": "Y", "kind": "run out"}]),
        ball(wickets=[{"player_out": "V Kohli", "kind": "retired hurt"}]),
    ]), "m", "tests"))
    assert [batter_outcome(r) for r in rows] == [
        None, OutcomeType.DOT, OutcomeType.FOUR, OutcomeType.CAUGHT, OutcomeType.DOT, OutcomeType.DOT,
    ]


def test_counts_group_chase_by_pressure():
    rows = list(parse_match(match([ball(runs=1), ball("Other", runs=6)], {"runs": 25, "overs": 2}), "m", "ipl"))
    counts = batting_counts(rows)
    assert counts["kohli"]["ipl"]["all"] == {"1": 1}
    assert counts["kohli"]["ipl"][Pressure.HIGH.value] == {"1": 1}


def test_match_state():
    s = MatchState(target=30, runs=12, balls_bowled=6, lives_lost=1)
    assert (s.balls_left, s.runs_needed, s.lives_left, s.required_rate) == (12, 18, 2, 9.0)
    assert s.pressure is Pressure.MEDIUM and not s.is_over
    assert MatchState(target=5, runs=5).batter_won
    assert MatchState(target=5, lives_lost=3).is_over


def test_career_stats_have_both_batters():
    stats = load_career_stats()
    assert stats["tendulkar", "tests", "average"] == 53.78
    assert stats["kohli", "tests", "runs"] == 9230
