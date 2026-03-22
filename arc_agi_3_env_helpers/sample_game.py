from __future__ import annotations

from arcengine import ARCBaseGame, BlockingMode, Camera, GameAction, GameState, InteractionMode, Level, Sprite


class SampleArcAgi3Game(ARCBaseGame):
    def __init__(self, max_actions: int = 16) -> None:
        self._max_actions = max_actions
        self._remaining_actions = max_actions

        wall = Sprite(
            pixels=[
                [5, 5, 5, 5, 5],
                [5, -1, -1, -1, 5],
                [5, -1, -1, -1, 5],
                [5, -1, -1, -1, 5],
                [5, 5, 5, 5, 5],
            ],
            name="wall",
            blocking=BlockingMode.PIXEL_PERFECT,
            interaction=InteractionMode.TANGIBLE,
            layer=-1,
        )
        player = Sprite([[8]], name="player", x=1, y=1, blocking=BlockingMode.BOUNDING_BOX)
        goal = Sprite([[9]], name="goal", x=3, y=3, blocking=BlockingMode.BOUNDING_BOX)

        level = Level(sprites=[wall, player, goal], grid_size=(5, 5))
        super().__init__(
            game_id="sample_arc_agi_3_game",
            levels=[level],
            camera=Camera(width=5, height=5, background=0, letter_box=0),
            available_actions=[1, 2, 3, 4, 5, 6, 7],
        )

    def full_reset(self) -> None:
        super().full_reset()
        self._remaining_actions = self._max_actions

    def level_reset(self) -> None:
        super().level_reset()
        self._remaining_actions = self._max_actions

    def remaining_budget(self) -> int:
        return self._remaining_actions

    def step(self) -> None:
        dx = 0
        dy = 0

        if self.action.id == GameAction.ACTION1:
            dy = -1
        elif self.action.id == GameAction.ACTION2:
            dy = 1
        elif self.action.id == GameAction.ACTION3:
            dx = -1
        elif self.action.id == GameAction.ACTION4:
            dx = 1
        elif self.action.id == GameAction.ACTION6:
            click_x = int(self.action.data.get("x", -1))
            click_y = int(self.action.data.get("y", -1))
            if click_x == 38 and click_y == 38:
                self.win()
            self._consume_action()
            self.complete_action()
            return

        collided = self.try_move("player", dx, dy)
        if collided and any(sprite.name == "goal" for sprite in collided):
            self.win()
            self.complete_action()
            return

        self._consume_action()
        self.complete_action()

    def _consume_action(self) -> None:
        if self.action.id != GameAction.RESET and self._remaining_actions > 0:
            self._remaining_actions -= 1
        if self._remaining_actions <= 0 and self._state != GameState.WIN:
            self.lose()


def create_game(max_actions: int = 16) -> SampleArcAgi3Game:
    return SampleArcAgi3Game(max_actions=max_actions)
