from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_task_specs(path: Path, *, default_game_factory: str) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        task_specs = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        loaded = json.loads(raw)
        if not isinstance(loaded, list):
            raise ValueError(f"Expected a JSON list of task specs in {path}.")
        task_specs = loaded

    normalized: list[dict[str, Any]] = []
    for index, task_spec in enumerate(task_specs):
        if not isinstance(task_spec, dict):
            raise ValueError(f"Task spec at index {index} is not a JSON object.")
        normalized.append(
            {
                "task_id": task_spec.get("task_id", f"task-{index}"),
                "instructions": task_spec.get("instructions"),
                "game_factory": task_spec.get("game_factory", default_game_factory),
                "game_kwargs": task_spec.get("game_kwargs", {}),
                "metadata": task_spec.get("metadata", {}),
            }
        )
    return normalized

