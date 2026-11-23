"""Pygame batting screen. Run: python -m duel.game --matchup tendulkar-bumrah"""
from __future__ import annotations

import argparse
import math

import pygame

from duel.engine import BallResult, Duel
from duel.matchup import MATCHUPS, load_matchup
from duel.types import Shot, ShotType

WIDTH, HEIGHT = 960, 540
GROUND_Y = 400
BATTER_X = 700
SWING_SECONDS = 0.45
RESULT_SECONDS = 1.1

SKY = (135, 196, 235)
GRASS = (66, 140, 72)
PITCH = (205, 178, 120)
INK = (24, 30, 38)
PANEL = (20, 36, 48)
WHITE = (245, 245, 240)
GOLD = (245, 200, 70)
RED = (220, 70, 60)
SHIRT = {"tendulkar": (60, 110, 200), "kohli": (30, 60, 150)}

SHOT_KEYS = {
    pygame.K_1: ShotType.LEAVE,
    pygame.K_2: ShotType.DEFEND,
    pygame.K_3: ShotType.WORK,
    pygame.K_4: ShotType.DRIVE,
    pygame.K_5: ShotType.CUT,
    pygame.K_6: ShotType.PULL,
    pygame.K_7: ShotType.SWEEP,
    pygame.K_8: ShotType.LOFT,
}
# Bat angle in degrees (0 points down, positive towards the bowler): backlift, finish.
SHOT_SWING = {
    ShotType.LEAVE: (20, 150),
    ShotType.DEFEND: (30, 12),
    ShotType.WORK: (60, -50),
    ShotType.DRIVE: (140, 60),
    ShotType.CUT: (120, 90),
    ShotType.PULL: (130, -100),
    ShotType.SWEEP: (110, -70),
    ShotType.LOFT: (150, -150),
}
NAMES = {"tendulkar": "Sachin Tendulkar", "kohli": "Virat Kohli", "bumrah": "Jasprit Bumrah", "warne": "Shane Warne"}


class GameScreen:
    """Holds the duel and animation state. `update` and `draw` need no real window."""

    def __init__(self, duel: Duel):
        self.duel = duel
        self.phase = "ready"
        self.clock = 0.0
        self.shot: ShotType | None = None
        self.result: BallResult | None = None
        self.big = pygame.font.SysFont("arial", 34, bold=True)
        self.mid = pygame.font.SysFont("arial", 22, bold=True)
        self.small = pygame.font.SysFont("arial", 16)
        duel.next_delivery()

    def choose(self, shot: ShotType) -> None:
        if self.phase == "ready":
            self.shot = shot
            self.phase = "swing"
            self.clock = 0.0

    def update(self, dt: float) -> None:
        self.clock += dt
        if self.phase == "swing" and self.clock >= SWING_SECONDS:
            self.result = self.duel.play(Shot(self.shot))
            self.phase = "result"
            self.clock = 0.0
        elif self.phase == "result" and self.clock >= RESULT_SECONDS:
            if self.duel.state.is_over:
                self.phase = "over"
            else:
                self.duel.next_delivery()
                self.phase = "ready"
                self.shot = None
            self.clock = 0.0

    def _bat_angle(self) -> float:
        if self.shot is None:
            return 18.0
        back, finish = SHOT_SWING[self.shot]
        if self.phase == "swing":
            t = min(self.clock / SWING_SECONDS, 1)
            return back + (finish - back) * t * t
        return finish

    def _text(self, surface, text, font, color, pos, center=False):
        image = font.render(text, True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        surface.blit(image, rect)

    def _draw_ground(self, surface):
        surface.fill(SKY)
        pygame.draw.rect(surface, GRASS, (0, GROUND_Y - 30, WIDTH, HEIGHT - GROUND_Y + 30))
        pygame.draw.polygon(
            surface, PITCH,
            [(110, GROUND_Y + 30), (850, GROUND_Y + 30), (800, GROUND_Y - 12), (160, GROUND_Y - 12)],
        )
        for x in (BATTER_X + 62, 190):
            for offset in (-4, 0, 4):
                pygame.draw.line(surface, WHITE, (x + offset, GROUND_Y + 8), (x + offset, GROUND_Y - 38), 2)

    def _draw_batter(self, surface):
        x, y = BATTER_X, GROUND_Y
        crouch = 8 if self.shot in (ShotType.SWEEP, ShotType.DEFEND) else 0
        hip = (x, y - 52 + crouch)
        neck = (x - 3, y - 104 + crouch)
        pygame.draw.line(surface, WHITE, hip, (x - 18, y + 4), 9)
        pygame.draw.line(surface, WHITE, hip, (x + 18, y + 4), 9)
        pygame.draw.line(surface, SHIRT[self.duel.matchup.batter.player], hip, neck, 18)
        pygame.draw.circle(surface, (196, 146, 108), (neck[0], neck[1] - 17), 13)
        pygame.draw.arc(surface, (28, 54, 120), (neck[0] - 14, neck[1] - 33, 28, 26), 0, math.pi, 7)
        hands = (x - 24, y - 72 + crouch)
        pygame.draw.line(surface, (196, 146, 108), (neck[0], neck[1] + 10), hands, 6)
        angle = math.radians(self._bat_angle())
        tip = (hands[0] - 62 * math.sin(angle), hands[1] + 62 * math.cos(angle))
        pygame.draw.line(surface, (232, 208, 150), hands, tip, 8)

    def _draw_ball(self, surface):
        delivery = self.duel.delivery
        if self.phase == "swing":
            t = min(self.clock / SWING_SECONDS, 1)
            pygame.draw.circle(surface, RED, (int(230 + (BATTER_X - 255) * t), int(GROUND_Y - 58 + 44 * math.sin(t * math.pi))), 6)
        elif self.phase == "result" and self.result and self.result.outcome.runs:
            t = min(self.clock / RESULT_SECONDS, 1)
            height = 190 if self.result.outcome.runs == 6 else 34
            pygame.draw.circle(surface, RED, (int(BATTER_X - 40 - 620 * t), int(GROUND_Y - 62 - height * math.sin(t * math.pi))), 6)
        elif delivery is not None and self.phase == "ready":
            pygame.draw.circle(surface, RED, (230, GROUND_Y - 58), 6)

    def _draw_scoreboard(self, surface):
        s = self.duel.state
        pygame.draw.rect(surface, PANEL, (0, 0, WIDTH, 84))
        m = self.duel.matchup
        self._text(surface, f"{NAMES[m.batter.player]} vs {NAMES[m.bowler.player]}", self.mid, WHITE, (20, 10))
        self._text(surface, f"{s.runs} / {s.lives_lost}", self.big, GOLD, (20, 40))
        over = f"{s.balls_bowled // 6}.{s.balls_bowled % 6} of {s.overs} overs"
        self._text(surface, over, self.small, WHITE, (165, 52))
        self._text(surface, f"Target {s.target}   Need {s.runs_needed} off {s.balls_left}", self.mid, WHITE, (500, 10))
        rate = "-" if math.isinf(s.required_rate) else f"{s.required_rate:.1f}"
        self._text(surface, f"Required rate {rate}   Pressure {s.pressure.value}", self.small, WHITE, (500, 40))
        self._text(surface, "Lives", self.small, WHITE, (500, 61))
        for i in range(s.lives):
            color = RED if i < s.lives_left else (80, 88, 96)
            pygame.draw.circle(surface, color, (556 + i * 20, 71), 7)

    def _draw_panel(self, surface):
        pygame.draw.rect(surface, PANEL, (0, HEIGHT - 92, WIDTH, 92))
        delivery = self.duel.delivery
        if delivery is not None and self.phase == "ready":
            text = f"Next ball: {delivery.bowl_type.value}, {delivery.length.value}, {delivery.line.value.replace('_', ' ')}"
            self._text(surface, text, self.mid, GOLD, (20, HEIGHT - 86))
        elif self.result is not None:
            r = self.result
            self._text(surface, f"{r.shot.shot_type.value} to a {r.delivery.length.value} ball", self.mid, WHITE, (20, HEIGHT - 86))
        keys = "   ".join(f"{i + 1} {shot.value}" for i, shot in enumerate(ShotType))
        hint = keys if self.phase != "over" else "R play again    Esc quit"
        self._text(surface, hint, self.small, WHITE, (20, HEIGHT - 46))
        self._text(surface, "Data: Cricsheet (CC BY 4.0)", self.small, (160, 172, 180), (20, HEIGHT - 24))

    def _draw_banner(self, surface):
        if self.phase == "result" and self.result:
            outcome = self.result.outcome
            label = outcome.kind.value.replace("_", " ").upper() if outcome.is_wicket else (
                "DOT BALL" if outcome.runs == 0 else f"{outcome.runs} RUN{'S' if outcome.runs > 1 else ''}"
            )
            self._text(surface, label, self.big, RED if outcome.is_wicket else GOLD, (WIDTH // 2, 140), True)
        elif self.phase == "over":
            won = self.duel.state.batter_won
            self._text(surface, "BATTER WINS" if won else "BOWLER WINS", self.big, GOLD if won else RED, (WIDTH // 2, 140), True)

    def draw(self, surface) -> None:
        self._draw_ground(surface)
        self._draw_ball(surface)
        self._draw_batter(surface)
        self._draw_scoreboard(surface)
        self._draw_panel(surface)
        self._draw_banner(surface)


def main() -> None:
    choices = [f"{a}-{b}" for a, b in MATCHUPS]
    parser = argparse.ArgumentParser(description="Cross-Era Cricket Duel: human bats")
    parser.add_argument("--matchup", choices=choices, default=choices[0])
    parser.add_argument("--overs", type=int, default=3)
    parser.add_argument("--lives", type=int, default=3)
    parser.add_argument("--target", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    print("Loading player networks...")
    matchup = load_matchup(*args.matchup.split("-"))

    def new_game() -> GameScreen:
        return GameScreen(Duel(matchup, args.target, args.overs, args.lives, args.seed))

    pygame.init()
    surface = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cross-Era Cricket Duel")
    clock = pygame.time.Clock()
    screen = new_game()
    running = True
    while running:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r and screen.phase == "over":
                    screen = new_game()
                elif event.key in SHOT_KEYS:
                    screen.choose(SHOT_KEYS[event.key])
        screen.update(dt)
        screen.draw(surface)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
