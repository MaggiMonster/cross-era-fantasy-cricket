import pytest

from duel.engine import Duel, default_target
from duel.matchup import MATCHUPS, load_matchup
from duel.types import Outcome, OutcomeType, Shot, ShotType


@pytest.fixture(scope="module", params=MATCHUPS, ids=lambda m: f"{m[0]}-{m[1]}")
def matchup(request):
    return load_matchup(*request.param)


def force(matchup, monkeypatch, kind):
    monkeypatch.setattr(matchup, "sample_outcome", lambda *a: Outcome(kind))


def test_default_target_uses_real_scoring_rate():
    assert default_target("kohli") > default_target("tendulkar") > 18
    assert default_target("kohli", 6) > default_target("kohli", 3)


def test_runs_and_balls_update(matchup, monkeypatch):
    force(matchup, monkeypatch, OutcomeType.FOUR)
    duel = Duel(matchup, target=20, seed=1)
    result = duel.play(Shot(ShotType.DRIVE))
    assert (result.before.runs, result.after.runs, result.after.balls_bowled) == (0, 4, 1)
    assert result.shot == Shot(ShotType.DRIVE)


def test_batter_wins_on_reaching_target(matchup, monkeypatch):
    force(matchup, monkeypatch, OutcomeType.SIX)
    duel = Duel(matchup, target=7, seed=1)
    duel.play()
    assert not duel.state.is_over
    duel.play()
    assert duel.state.batter_won and duel.state.is_over
    with pytest.raises(RuntimeError):
        duel.play()


def test_lives_end_the_duel(matchup, monkeypatch):
    force(matchup, monkeypatch, OutcomeType.BOWLED)
    duel = Duel(matchup, target=20, lives=2, seed=1)
    duel.play()
    assert duel.state.lives_left == 1
    duel.play()
    assert duel.state.is_over and not duel.state.batter_won


def test_overs_end_the_duel(matchup, monkeypatch):
    force(matchup, monkeypatch, OutcomeType.DOT)
    duel = Duel(matchup, target=20, overs=1, seed=1)
    for _ in range(6):
        duel.play()
    assert duel.state.is_over and len(duel.history) == 6


def test_delivery_is_stable_until_played(matchup):
    duel = Duel(matchup, target=20, seed=3)
    delivery = duel.next_delivery()
    assert duel.next_delivery() == delivery
    assert duel.play().delivery == delivery


def test_same_seed_same_duel(matchup):
    def run():
        duel = Duel(matchup, seed=11)
        while not duel.state.is_over:
            duel.play()
        return [(r.delivery, r.shot, r.outcome) for r in duel.history]

    assert run() == run()


@pytest.mark.parametrize("kwargs", [{"overs": 0}, {"lives": 0}, {"target": 0}])
def test_rejects_bad_settings(matchup, kwargs):
    with pytest.raises(ValueError):
        Duel(matchup, **kwargs)
