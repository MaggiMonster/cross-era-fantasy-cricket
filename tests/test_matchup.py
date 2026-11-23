import numpy as np
import pytest

from duel.batting import OUTCOMES, PRESSURES, SHOTS, WICKET_MASK
from duel.matchup import MATCHUPS, Matchup, load_matchup
from duel.types import Length, Line, MatchState, Outcome, Pressure, Shot, ShotType


@pytest.fixture(scope="module", params=MATCHUPS, ids=lambda m: f"{m[0]}-{m[1]}")
def duel(request):
    return load_matchup(*request.param)


def all_deliveries(duel):
    from duel.types import Delivery

    return [Delivery(duel.bowler.bowl_type, l, m) for l in Length for m in Line]


def test_probabilities_valid_everywhere(duel):
    for delivery in all_deliveries(duel):
        for pressure in PRESSURES:
            for shot in SHOTS:
                p = np.array(list(duel.outcome_probs(delivery, Shot(shot), pressure).values()))
                assert p.sum() == pytest.approx(1)
                assert (p > 0).all()


def test_average_bowler_returns_the_batter(duel):
    """If the bowler equals the baseline, log5 must give the batter's own table."""
    average = Matchup(duel.batter, duel.bowler, duel.baseline)
    delivery = all_deliveries(duel)[7]
    shot, pressure = Shot(ShotType.DRIVE), Pressure.MEDIUM
    base = duel.baseline_probs(delivery, pressure)
    average.bowler = type("Average", (), {"outcome_probs": lambda self, d, p: dict(zip(OUTCOMES, base.tolist()))})()
    got = list(average.outcome_probs(delivery, shot, pressure).values())
    assert got == pytest.approx(list(duel.batter.outcome_probs(delivery, shot, pressure).values()))


def test_better_bowler_raises_wicket_risk(duel):
    """Scaling the bowler's wicket odds up must raise the combined wicket probability."""
    delivery = all_deliveries(duel)[7]
    shot, pressure = Shot(ShotType.DRIVE), Pressure.MEDIUM
    before = np.array(list(duel.outcome_probs(delivery, shot, pressure).values()))[WICKET_MASK].sum()
    real = duel.bowler.outcome_probs(delivery, pressure)
    boosted = {o: v * (2 if o.is_wicket else 1) for o, v in real.items()}
    total = sum(boosted.values())
    boosted = {o: v / total for o, v in boosted.items()}
    stronger = Matchup(duel.batter, type("Strong", (), {"outcome_probs": lambda self, d, p: boosted})(), duel.baseline)
    after = np.array(list(stronger.outcome_probs(delivery, shot, pressure).values()))[WICKET_MASK].sum()
    assert after > before


def test_full_ball_sampling_is_reproducible(duel):
    state = MatchState(target=30)

    def play(seed):
        rng = np.random.default_rng(seed)
        delivery = duel.bowler.sample_delivery(state, rng)
        shot = duel.batter.sample_shot(delivery, state, rng)
        return delivery, shot, duel.sample_outcome(delivery, shot, state, rng)

    assert play(5) == play(5)
    assert isinstance(play(5)[2], Outcome)


@pytest.mark.parametrize("pair", [("tendulkar", "warne"), ("kohli", "bumrah"), ("bumrah", "kohli")])
def test_only_old_vs_new(pair):
    with pytest.raises(ValueError):
        load_matchup(*pair)
