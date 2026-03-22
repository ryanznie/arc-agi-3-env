from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from arc_agi_3_env_helpers.tasks import load_task_specs

DEFAULT_TASKS_PATH = Path(str(files("tasks").joinpath("sample_tasks.json")))
DEFAULT_GAME_FACTORY = "arc_agi_3_env_helpers.sample_game:create_game"


def _load_verifiers():
    try:
        import verifiers as vf
    except ImportError as exc:  # pragma: no cover - depends on external install
        raise RuntimeError(
            "The 'verifiers' package is required to use this environment. "
            "Install PrimeIntellect verifiers first."
        ) from exc
    return vf


def _build_dataset_rows(task_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task_spec in task_specs:
        rows.append(
            {
                "prompt": [{"role": "user", "content": "Initializing ARC-AGI 3 environment..."}],
                "info": json.dumps(task_spec, separators=(",", ":")),
            }
        )
    return rows


def load_environment(
    tasks_path: str | None = None,
    game_factory: str = DEFAULT_GAME_FACTORY,
    max_turns: int = 256,
    **kwargs: Any,
):
    vf = _load_verifiers()
    from datasets import Dataset

    from arc_agi_3_env_helpers.actions import parse_action_payload
    from arc_agi_3_env_helpers.engine import EngineSession
    from arc_agi_3_env_helpers.formatting import build_feedback_message, build_initial_prompt

    resolved_tasks_path = Path(tasks_path) if tasks_path is not None else DEFAULT_TASKS_PATH
    task_specs = load_task_specs(resolved_tasks_path, default_game_factory=game_factory)
    dataset = Dataset.from_list(_build_dataset_rows(task_specs))

    async def solved_reward(state) -> float:
        return 1.0 if state.get("solved", False) else 0.0

    async def truncated_reward(state) -> float:
        return 0.0 if state.get("truncated", False) else 0.0

    rubric = vf.Rubric(funcs=[solved_reward, truncated_reward], weights=[1.0, 0.0])

    class ArcAgi3Env(vf.MultiTurnEnv):
        async def setup_state(self, state):
            state = await super().setup_state(state)

            task_spec = json.loads(state["info"])
            session = EngineSession.from_task_spec(task_spec)
            transition = session.reset()

            state["task_spec"] = task_spec
            state["session"] = session
            state["steps_taken"] = 0
            state["invalid_action_count"] = 0
            state["solved"] = transition.solved
            state["truncated"] = transition.truncated
            state["done_reason"] = transition.done_reason
            state["last_transition"] = transition.to_dict()
            state["prompt"] = build_initial_prompt(task_spec=task_spec, transition=transition)
            return state

        async def get_prompt_messages(self, state):
            return state["prompt"]

        async def env_response(self, messages, state):
            session: EngineSession = state["session"]
            last_message = messages[-1] if messages else {"content": ""}
            parsed_action = parse_action_payload(last_message.get("content", ""))

            transition = session.step(parsed_action)
            if transition.step_consumed:
                state["steps_taken"] += 1
            if not parsed_action.valid:
                state["invalid_action_count"] += 1

            state["solved"] = transition.solved
            state["truncated"] = transition.truncated
            state["done_reason"] = transition.done_reason
            state["last_transition"] = transition.to_dict()

            feedback = build_feedback_message(
                transition=transition,
                invalid_action_count=state["invalid_action_count"],
            )
            response = [{"role": "user", "content": feedback}]

            if transition.done:
                state["final_env_response"] = response

            return response

        @vf.stop
        async def game_finished(self, state) -> bool:
            return bool(state.get("solved") or state.get("truncated"))

    return ArcAgi3Env(dataset=dataset, rubric=rubric, max_turns=max_turns, **kwargs)
