import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from duel.engine import Duel
from duel.game import HEIGHT, RESULT_SECONDS, SHOT_KEYS, SWING_SECONDS, WIDTH, GameScreen
from duel.matchup import MATCHUPS, load_matchup
from duel.types import ShotType


@pytest.fixture(scope="module", autouse=True)
def display():
    pygame.init()
    yield pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.quit()


@pytest.fixture(scope="module", params=MATCHUPS, ids=lambda m: f"{m[0]}-{m[1]}")
def matchup(request):
    return load_matchup(*request.param)


def test_every_shot_has_a_key():
    assert set(SHOT_KEYS.values()) == set(ShotType)


def test_full_game_draws_every_phase(matchup, display):
    screen = GameScreen(Duel(matchup, seed=4))
    seen = set()
    for _ in range(200):
        screen.draw(display)
        seen.add(screen.phase)
        if screen.phase == "over":
            break
        screen.choose(ShotType.DRIVE)
        screen.update(SWING_SECONDS / 2)
        screen.draw(display)
        screen.update(SWING_SECONDS)
        screen.draw(display)
        seen.add(screen.phase)
        screen.update(RESULT_SECONDS)
    assert {"ready", "result", "over"} <= seen
    assert screen.duel.state.is_over


def test_input_ignored_during_swing(matchup):
    screen = GameScreen(Duel(matchup, seed=4))
    screen.choose(ShotType.DRIVE)
    screen.choose(ShotType.LOFT)
    assert screen.shot == ShotType.DRIVE
