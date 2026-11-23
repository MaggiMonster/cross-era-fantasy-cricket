import json

import numpy as np
import pytest
from pgmpy.inference import VariableElimination

from duel.batting import (
    OUTCOMES, PRESSURES, REFERENCE_BOWL, REFERENCE_LENGTH, REFERENCE_LINE, WICKET_MASK,
    load_batter, observed_rates,
)
from duel.career import load_career_stats
from duel.cricsheet import BATTERS, BATTING_COUNTS
from duel.types import BowlType, Delivery, Length, Line, MatchState, OutcomeType, Pressure, Shot, ShotType

YORKER = Delivery(BowlType.PACE, Length.YORKER, Line.STUMPS)
BOUNCER = Delivery(BowlType.PACE, Length.BOUNCER, Line.STUMPS)
SPIN = Delivery(BowlType.SPIN, Length.GOOD, Line.LEG)


@pytest.fixture(scope="module", params=BATTERS)
def net(request):
    return load_batter(request.param)


@pytest.fixture(scope="module")
def rates():
    counts = json.loads(BATTING_COUNTS.read_text())["players"]
    return {b: observed_rates(b, counts, load_career_stats()) for b in BATTERS}


def test_model_valid_and_tables_normalised(net):
    assert net.model.check_model()
    assert np.allclose(net.shot_table.sum(-1), 1)
    assert np.allclose(net.outcome_table.sum(-1), 1)
    assert (net.outcome_table > 0).all()


def test_calibrated_to_observed_rates(net, rates):
    for i, pressure in enumerate(PRESSURES):
        by_line = (net.shot_table[i] * REFERENCE_LINE[None, None, :, None]).sum(axis=2)
        joint = np.einsum("b,bl,bls->sbl", REFERENCE_BOWL, REFERENCE_LENGTH, by_line)
        marginal = np.einsum("sbl,sblo->o", joint, net.outcome_table[i])
        assert marginal == pytest.approx(rates[net.player][pressure], abs=1e-6)


def test_pgmpy_inference_matches_lookup(net):
    infer = VariableElimination(net.model)
    q = infer.query(["Shot"], evidence={"Pressure": "high", "BowlType": "spin", "Length": "good", "Line": "leg"}, show_progress=False)
    expected = net.shot_probs(SPIN, Pressure.HIGH)
    assert [q.get_value(Shot=s.value) for s in expected] == pytest.approx(list(expected.values()))
    q = infer.query(["Outcome"], evidence={"Pressure": "low", "Shot": "drive", "BowlType": "pace", "Length": "yorker"}, show_progress=False)
    expected = net.outcome_probs(YORKER, Shot(ShotType.DRIVE), Pressure.LOW)
    assert [q.get_value(Outcome=o.value) for o in expected] == pytest.approx(list(expected.values()))


def test_cricket_sense(net):
    attack = {ShotType.LOFT, ShotType.PULL, ShotType.DRIVE, ShotType.CUT}
    low = net.shot_probs(YORKER, Pressure.LOW)
    high = net.shot_probs(YORKER, Pressure.HIGH)
    assert sum(high[s] for s in attack) > sum(low[s] for s in attack)
    assert net.shot_probs(BOUNCER, Pressure.MEDIUM)[ShotType.PULL] > net.shot_probs(YORKER, Pressure.MEDIUM)[ShotType.PULL]
    assert net.shot_probs(SPIN, Pressure.MEDIUM)[ShotType.SWEEP] > net.shot_probs(Delivery(BowlType.PACE, Length.GOOD, Line.LEG), Pressure.MEDIUM)[ShotType.SWEEP]
    drive = Shot(ShotType.DRIVE)
    assert net.outcome_probs(YORKER, drive, Pressure.MEDIUM)[OutcomeType.BOWLED] > net.outcome_probs(BOUNCER, drive, Pressure.MEDIUM)[OutcomeType.BOWLED]
    loft = net.outcome_probs(SPIN, Shot(ShotType.LOFT), Pressure.MEDIUM)
    defend = net.outcome_probs(SPIN, Shot(ShotType.DEFEND), Pressure.MEDIUM)
    assert loft[OutcomeType.SIX] > defend[OutcomeType.SIX]


def test_sampling_is_reproducible(net):
    state = MatchState(target=30)
    a = [net.sample_shot(YORKER, state, np.random.default_rng(7)) for _ in range(3)]
    b = [net.sample_shot(YORKER, state, np.random.default_rng(7)) for _ in range(3)]
    assert a == b


def test_observed_rates_are_distributions(rates):
    for by_pressure in rates.values():
        for p in by_pressure.values():
            assert p.sum() == pytest.approx(1)
            assert 0.005 < p[WICKET_MASK].sum() < 0.15


def test_unknown_batter():
    with pytest.raises(ValueError):
        load_batter("bumrah")
