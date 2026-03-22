from __future__ import annotations

import random
from typing import Any

from arc_agi_3_env_helpers.engine import EngineSession


class RandomPolicy:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def choose_action(self, session: EngineSession) -> dict[str, Any]:
        valid_actions = session.valid_actions()
        if valid_actions:
            return self._rng.choice(valid_actions)
        fallback = [
            {"action": "ACTION1"},
            {"action": "ACTION2"},
            {"action": "ACTION3"},
            {"action": "ACTION4"},
            {"action": "ACTION5"},
            {"action": "ACTION7"},
        ]
        return self._rng.choice(fallback)

