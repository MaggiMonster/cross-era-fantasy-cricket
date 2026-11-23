import json

import numpy as np
import pytest

from duel.batting import BOWL_TYPES, OUTCOMES, PRESSURES, WICKET_MASK, load_batter
from duel.cricsheet import BATTERS
from duel.pace_spin import MAX_EFFECT, PACE_SPIN_COUNTS, STYLES, load_bowler_types, player_effects
from duel.types import BowlType, Delivery, Length, Line, OutcomeType, Pressure, Shot, ShotType


@pytest.fixture(scope="module")
def data():
    return json.loads(PACE_SPIN_COUNTS.read_text())


def wicket_risk(net, bowl_type):
    delivery = Delivery(bowl_type, Length.GOOD, Line.STUMPS)
    p = np.array(list(net.outcome_probs(delivery, Shot(ShotType.DRIVE), Pressure.MEDIUM).values()))
    stumped = OUTCOMES.index(OutcomeType.STUMPED)
    keep = WICKET_MASK.copy()
    keep[stumped] = False  # Stumpings differ by bowling type for every batter.
    return p[keep].sum()


def test_labels_are_valid_and_cover_most_balls(data):
    assert set(load_bowler_types().values()) == set(STYLES)
    assert all(share > 0.9 for share in data["coverage"].values())


@pytest.mark.parametrize("player", BATTERS)
def test_effects_are_bounded(player, data):
    for by_event in player_effects(player, data).values():
        for value in by_event.values():
            assert 1 / MAX_EFFECT <= value <= MAX_EFFECT


def test_each_batter_has_the_measured_strength(data):
    sachin = player_effects("tendulkar", data)
    kohli = player_effects("kohli", data)
    assert sachin[BowlType.PACE]["wicket"] < sachin[BowlType.SPIN]["wicket"]
    assert kohli[BowlType.SPIN]["wicket"] < kohli[BowlType.PACE]["wicket"]


def test_adjustment_reaches_the_network():
    sachin, kohli = load_batter("tendulkar"), load_batter("kohli")
    sachin_ratio = wicket_risk(sachin, BowlType.SPIN) / wicket_risk(sachin, BowlType.PACE)
    kohli_ratio = wicket_risk(kohli, BowlType.SPIN) / wicket_risk(kohli, BowlType.PACE)
    assert sachin_ratio > kohli_ratio


@pytest.mark.parametrize("player", BATTERS)
def test_tables_stay_normalised(player):
    net = load_batter(player)
    assert np.allclose(net.outcome_table.sum(-1), 1)
    assert net.outcome_table.shape[0] == len(PRESSURES)
    assert net.outcome_table.shape[2] == len(BOWL_TYPES)
