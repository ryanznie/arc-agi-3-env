from __future__ import annotations

import json
from typing import Any

from arc_agi_3_env_helpers.engine import Transition


def build_initial_prompt(*, task_spec: dict[str, Any], transition: Transition) -> list[dict[str, str]]:
    user_content = "\n".join(
        [
            task_spec.get("instructions", DEFAULT_INSTRUCTIONS),
            "",
            "Respond with JSON only.",
            'Examples: {"action":"ACTION1"} or {"action":"ACTION6","x":12,"y":37}',
            "",
            _transition_block(transition),
        ]
    )
    return [{"role": "user", "content": user_content}]


def build_feedback_message(*, transition: Transition, invalid_action_count: int) -> str:
    lines = [_transition_block(transition), f"Invalid actions so far: {invalid_action_count}."]
    if not transition.done:
        lines.append('Return the next move as JSON only, for example {"action":"ACTION1"}.')
    return "\n\n".join(lines)


def _transition_block(transition: Transition) -> str:
    return "\n".join(
        [
            f"Action result: {json.dumps(transition.action, separators=(',', ':'))}",
            f"Solved: {str(transition.solved).lower()}",
            f"Truncated: {str(transition.truncated).lower()}",
            f"Step consumed: {str(transition.step_consumed).lower()}",
            f"Remaining budget: {transition.remaining_budget}",
            f"Invalid action: {str(transition.invalid_action).lower()}",
            f"Invalid reason: {transition.invalid_reason}",
            "Observation:",
            json.dumps(transition.observation, separators=(",", ":")),
        ]
    )


DEFAULT_INSTRUCTIONS = (
    "You are interacting with an ARC-AGI 3 style environment. "
    "Choose exactly one action per turn. "
    "Available actions are RESET, ACTION1, ACTION2, ACTION3, ACTION4, ACTION5, ACTION6(x,y), ACTION7. "
    "ACTION1-4 roughly map to up/down/left/right. ACTION5 is a contextual action. "
    "ACTION7 is undo. Invalid actions are ignored and do not consume budget."
)

