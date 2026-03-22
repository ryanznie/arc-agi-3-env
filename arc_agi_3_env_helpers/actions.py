from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

VALID_ACTIONS = {
    "RESET",
    "ACTION1",
    "ACTION2",
    "ACTION3",
    "ACTION4",
    "ACTION5",
    "ACTION6",
    "ACTION7",
}


@dataclass(slots=True)
class ParsedAction:
    valid: bool
    action: str | None
    x: int | None = None
    y: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "action": self.action,
            "x": self.x,
            "y": self.y,
            "error": self.error,
        }


def parse_action_payload(payload: str) -> ParsedAction:
    payload = payload.strip()
    if not payload:
        return ParsedAction(valid=False, action=None, error="Empty response.")

    json_blob = _extract_json_blob(payload)
    if json_blob is None:
        if payload in VALID_ACTIONS:
            return ParsedAction(valid=True, action=payload)
        return ParsedAction(valid=False, action=None, error="Expected JSON action payload.")

    try:
        parsed = json.loads(json_blob)
    except json.JSONDecodeError:
        return ParsedAction(valid=False, action=None, error="Invalid JSON.")

    if not isinstance(parsed, dict):
        return ParsedAction(valid=False, action=None, error="Action payload must be a JSON object.")

    action = parsed.get("action") or parsed.get("id")
    if not isinstance(action, str):
        return ParsedAction(valid=False, action=None, error="Missing string action field.")

    action = action.upper()
    if action not in VALID_ACTIONS:
        return ParsedAction(valid=False, action=None, error=f"Unsupported action '{action}'.")

    if action == "ACTION6":
        x = parsed.get("x")
        y = parsed.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return ParsedAction(valid=False, action=action, error="ACTION6 requires integer x and y.")
        if not 0 <= x <= 63 or not 0 <= y <= 63:
            return ParsedAction(valid=False, action=action, error="ACTION6 coordinates must be in [0, 63].")
        return ParsedAction(valid=True, action=action, x=x, y=y)

    return ParsedAction(valid=True, action=action)


def _extract_json_blob(payload: str) -> str | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", payload, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    return payload[start : end + 1]

