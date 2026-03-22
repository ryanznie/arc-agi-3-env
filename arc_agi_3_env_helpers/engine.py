from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from arcengine import ActionInput, GameAction, GameState

from arc_agi_3_env_helpers.actions import ParsedAction
from arc_agi_3_env_helpers.factory import load_factory


@dataclass(slots=True)
class Transition:
    observation: list[list[int]]
    frames: list[list[list[int]]]
    record_data: dict[str, Any] | None
    solved: bool
    truncated: bool
    done: bool
    done_reason: str | None
    step_consumed: bool
    remaining_budget: int | None
    invalid_action: bool
    invalid_reason: str | None
    action: dict[str, Any]
    available_actions: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frames": self.frames,
            "record_data": self.record_data,
            "solved": self.solved,
            "truncated": self.truncated,
            "done": self.done,
            "done_reason": self.done_reason,
            "step_consumed": self.step_consumed,
            "remaining_budget": self.remaining_budget,
            "invalid_action": self.invalid_action,
            "invalid_reason": self.invalid_reason,
            "action": self.action,
            "available_actions": self.available_actions,
        }


class EngineSession:
    def __init__(self, *, game) -> None:
        self.game = game

    @classmethod
    def from_task_spec(cls, task_spec: dict[str, Any]) -> "EngineSession":
        factory = load_factory(task_spec["game_factory"])
        game_kwargs = task_spec.get("game_kwargs", {})
        game = factory(**game_kwargs)
        return cls(game=game)

    def reset(self) -> Transition:
        if hasattr(self.game, "full_reset"):
            self.game.full_reset()
        return self._transition_from_current_state(
            action={"action": "RESET"},
            step_consumed=False,
            invalid_action=False,
            invalid_reason=None,
        )

    def valid_actions(self) -> list[dict[str, Any]]:
        get_valid_actions = getattr(self.game, "_get_valid_actions", None)
        if not callable(get_valid_actions):
            return []
        valid_actions = get_valid_actions()
        return [self._action_input_to_payload(action_input) for action_input in valid_actions]

    def step(self, parsed_action: ParsedAction) -> Transition:
        if not parsed_action.valid:
            return self._transition_from_current_state(
                action=parsed_action.to_dict(),
                step_consumed=False,
                invalid_action=True,
                invalid_reason=parsed_action.error,
            )

        action_input = self._to_action_input(parsed_action)
        frame_data = self.game.perform_action(action_input, raw=False)

        frames = frame_data.frame if frame_data.frame else [self._render_observation()]
        observation = frames[-1]
        record_data = json.loads(frame_data.model_dump_json())
        solved = frame_data.state == GameState.WIN
        remaining_budget = self._get_remaining_budget()
        truncated = (
            frame_data.state == GameState.GAME_OVER
            or (remaining_budget is not None and remaining_budget <= 0 and not solved)
        )
        done = solved or truncated
        done_reason = "solved" if solved else "budget_exhausted" if truncated else None

        return Transition(
            observation=observation,
            frames=frames,
            record_data=record_data,
            solved=solved,
            truncated=truncated,
            done=done,
            done_reason=done_reason,
            step_consumed=parsed_action.action != "RESET",
            remaining_budget=remaining_budget,
            invalid_action=False,
            invalid_reason=None,
            action=parsed_action.to_dict(),
            available_actions=list(getattr(frame_data, "available_actions", [])),
        )

    def _transition_from_current_state(
        self,
        *,
        action: dict[str, Any],
        step_consumed: bool,
        invalid_action: bool,
        invalid_reason: str | None,
    ) -> Transition:
        remaining_budget = self._get_remaining_budget()
        observation = self._render_observation()
        solved = getattr(self.game, "_state", None) == GameState.WIN
        truncated = (
            getattr(self.game, "_state", None) == GameState.GAME_OVER
            or (remaining_budget is not None and remaining_budget <= 0 and not solved)
        )
        done = solved or truncated
        done_reason = "solved" if solved else "budget_exhausted" if truncated else None

        return Transition(
            observation=observation,
            frames=[observation],
            record_data=None,
            solved=solved,
            truncated=truncated,
            done=done,
            done_reason=done_reason,
            step_consumed=step_consumed,
            remaining_budget=remaining_budget,
            invalid_action=invalid_action,
            invalid_reason=invalid_reason,
            action=action,
            available_actions=list(getattr(self.game, "_available_actions", [])),
        )

    def _render_observation(self) -> list[list[int]]:
        frame = self.game.camera.render(self.game.current_level.get_sprites())
        return frame.tolist()

    def _to_action_input(self, parsed_action: ParsedAction) -> ActionInput:
        game_action = GameAction.from_name(parsed_action.action or "RESET")
        data: dict[str, Any] = {}
        if parsed_action.action == "ACTION6":
            data = {"x": parsed_action.x, "y": parsed_action.y}
        return ActionInput(id=game_action, data=data)

    def _action_input_to_payload(self, action_input: ActionInput) -> dict[str, Any]:
        payload: dict[str, Any] = {"action": action_input.id.name}
        if action_input.id == GameAction.ACTION6:
            payload["x"] = int(action_input.data["x"])
            payload["y"] = int(action_input.data["y"])
        return payload

    def _get_remaining_budget(self) -> int | None:
        for attr_name in (
            "remaining_budget",
            "get_remaining_budget",
            "remaining_actions",
            "get_remaining_actions",
        ):
            value = getattr(self.game, attr_name, None)
            if callable(value):
                result = value()
            else:
                result = value
            if isinstance(result, int):
                return result

        ui = getattr(self.game, "_ui", None)
        sprite_pairs = getattr(ui, "_sprite_pairs", None)
        if sprite_pairs:
            remaining = 0
            for enabled_sprite, _ in sprite_pairs:
                if "energy" in getattr(enabled_sprite, "tags", []):
                    interaction = getattr(enabled_sprite, "interaction", None)
                    if getattr(interaction, "name", None) != "REMOVED":
                        remaining += 1
            return remaining

        return None
