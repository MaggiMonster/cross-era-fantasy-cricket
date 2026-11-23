import json

import numpy as np
import pytest
from pgmpy.inference import VariableElimination

from duel.batting import LENGTHS, LINES, OUTCOMES, PRESSURES, WICKET_MASK
from duel.bowling import _load_counts, baseline_table, load_bowler, observed_rates, population_rates
from duel.career import load_career_stats
from duel.cricsheet import BOWLERS, BOWLING_COUNTS, BowlingTally
from duel.types import BowlType, Delivery, Length, Line, MatchState, OutcomeType, Pressure


@pytest.fixture(scope="module", params=BOWLERS)
def net(request):
    return load_bowler(request.param)


@pytest.fixture(scope="module")
def rates():
    return {b: observed_rates(b, _load_counts(), load_career_stats()) for b in BOWLERS}


def own_delivery(net, length=Length.GOOD, line=Line.STUMPS):
    return Delivery(net.bowl_type, length, line)


def test_model_valid_and_tables_normalised(net):
    assert net.model.check_model()
    assert np.allclose(net.length_table.sum(-1), 1)
    assert np.allclose(net.line_table.sum(-1), 1)
    assert np.allclose(net.outcome_table.sum(-1), 1)
    assert (net.outcome_table > 0).all()


def test_calibrated_to_observed_rates(net, rates):
    for i, pressure in enumerate(PRESSURES):
        joint = net.length_table[i][:, None] * net.line_table
        marginal = np.einsum("lm,lmo->o", joint, net.outcome_table[i])
        assert marginal == pytest.approx(rates[net.player][pressure], abs=1e-6)


def test_pgmpy_inference_matches_lookup(net):
    infer = VariableElimination(net.model)
    q = infer.query(["Outcome"], evidence={"Pressure": "high", "Length": "full", "Line": "leg"}, show_progress=False)
    expected = net.outcome_probs(own_delivery(net, Length.FULL, Line.LEG), Pressure.HIGH)
    assert [q.get_value(Outcome=o.value) for o in expected] == pytest.approx(list(expected.values()))
    q = infer.query(["Length"], evidence={"Pressure": "high"}, show_progress=False)
    assert [q.get_value(Length=l.value) for l in LENGTHS] == pytest.approx(net.length_table[2].tolist())


def test_sampling_is_reproducible_and_matches_prior(net):
    state = MatchState(target=60)  # 20 an over: high pressure
    assert state.pressure is Pressure.HIGH
    a = [net.sample_delivery(state, np.random.default_rng(3)) for _ in range(3)]
    b = [net.sample_delivery(state, np.random.default_rng(3)) for _ in range(3)]
    assert a == b
    rng = np.random.default_rng(11)
    draws = [net.sample_delivery(state, rng) for _ in range(4000)]
    assert {d.bowl_type for d in draws} == {net.bowl_type}
    observed = np.mean([d.length is Length.GOOD for d in draws])
    assert observed == pytest.approx(net.length_table[2, LENGTHS.index(Length.GOOD)], abs=0.03)


def test_pace_and_spin_differ():
    bumrah, warne = load_bowler("bumrah"), load_bowler("warne")
    y = LENGTHS.index(Length.YORKER)
    h = PRESSURES.index(Pressure.HIGH)
    assert bumrah.length_table[h, y] > warne.length_table[h, y]
    assert bumrah.length_table[h, y] > bumrah.length_table[0, y]
    d_pace, d_spin = own_delivery(bumrah), own_delivery(warne)
    assert warne.outcome_probs(d_spin, Pressure.MEDIUM)[OutcomeType.STUMPED] > bumrah.outcome_probs(d_pace, Pressure.MEDIUM)[OutcomeType.STUMPED]


def test_bumrah_beats_population_on_wickets(rates):
    population = population_rates(_load_counts())
    for pressure in PRESSURES:
        assert rates["bumrah"][pressure][WICKET_MASK].sum() > 0.8 * population[pressure][WICKET_MASK].sum()
    overall = np.mean([rates["bumrah"][p][WICKET_MASK].sum() / population[p][WICKET_MASK].sum() for p in PRESSURES])
    assert overall > 1


def test_baseline_is_a_distribution():
    table = baseline_table()
    assert np.allclose(table.sum(-1), 1)
    assert (table > 0).all()


def test_wrong_bowl_type_rejected():
    bumrah = load_bowler("bumrah")
    with pytest.raises(ValueError):
        bumrah.outcome_probs(Delivery(BowlType.SPIN, Length.GOOD, Line.LEG), Pressure.LOW)


def test_unknown_bowler():
    with pytest.raises(ValueError):
        load_bowler("kohli")


def test_counts_match_published_bumrah_wickets():
    data = json.loads(BOWLING_COUNTS.read_text())
    assert data["players"]["bumrah"]["test_wickets"] == 234
    assert "CC BY 4.0" in data["source"]


def test_tally_charges_extras_but_not_run_outs():
    tally = BowlingTally()
    base = {"format": "tests", "bowler": "JJ Bumrah", "batter": "X", "required_rate": ""}
    tally.add({**base, "batter_runs": 4, "total_runs": 4, "wide": 0, "noball": 0, "dismissal": ""})
    tally.add({**base, "batter_runs": 0, "total_runs": 1, "wide": 1, "noball": 0, "dismissal": ""})
    tally.add({**base, "batter_runs": 0, "total_runs": 2, "wide": 0, "noball": 0, "dismissal": ""})  # byes
    tally.add({**base, "batter_runs": 0, "total_runs": 0, "wide": 0, "noball": 0, "dismissal": "run out"})
    tally.add({**base, "batter_runs": 0, "total_runs": 0, "wide": 0, "noball": 0, "dismissal": "bowled"})
    side = tally.result()["players"]["bumrah"]
    assert side["test_runs_conceded"] == 5
    assert side["test_wickets"] == 1
    assert sum(side["tests"]["all"].values()) == 4  # the wide is not a ball faced
