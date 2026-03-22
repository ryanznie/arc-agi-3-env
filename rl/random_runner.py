from __future__ import annotations

import argparse
import json
import random
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arc_agi_3_env_helpers.actions import ParsedAction
from arc_agi_3_env_helpers.engine import EngineSession, Transition
from arc_agi_3_env_helpers.tasks import load_task_specs
from rl.random_policy import RandomPolicy

DEFAULT_TASKS_PATH = Path(__file__).resolve().parents[1] / "evals" / "example_games.json"


@dataclass(slots=True)
class EpisodeResult:
    task_id: str
    episode_index: int
    seed: int
    solved: bool
    reward: float
    truncated: bool
    done_reason: str | None
    steps_taken: int
    invalid_actions: int
    remaining_budget: int | None


@dataclass(slots=True)
class StepRecord:
    step_index: int
    record_data: dict[str, Any] | None
    step_consumed: bool
    invalid_action: bool
    invalid_reason: str | None
    solved: bool
    truncated: bool
    done: bool
    done_reason: str | None
    remaining_budget: int | None
    frame_count: int
    frames: list[list[list[int]]]


@dataclass(slots=True)
class EpisodeArtifacts:
    result: EpisodeResult
    steps: list[StepRecord]


def run_episode(task_spec: dict[str, Any], *, seed: int, episode_index: int, max_steps: int) -> EpisodeArtifacts:
    rng = random.Random(seed)
    policy = RandomPolicy(rng)
    session = EngineSession.from_task_spec(task_spec)
    transition = session.reset()

    steps_taken = 0
    invalid_actions = 0
    step_records: list[StepRecord] = []

    while not transition.done and steps_taken < max_steps:
        action_payload = policy.choose_action(session)
        parsed_action = ParsedAction(
            valid=True,
            action=action_payload["action"],
            x=action_payload.get("x"),
            y=action_payload.get("y"),
        )
        transition = session.step(parsed_action)
        if transition.step_consumed:
            steps_taken += 1
        if transition.invalid_action:
            invalid_actions += 1
        step_records.append(_step_record(step_index=len(step_records), transition=transition))

    truncated = transition.truncated or (not transition.done and steps_taken >= max_steps)
    solved = transition.solved
    reward = 1.0 if solved else 0.0
    done_reason = transition.done_reason
    if not transition.done and steps_taken >= max_steps:
        done_reason = "max_steps"

    return EpisodeArtifacts(
        result=EpisodeResult(
            task_id=task_spec["task_id"],
            episode_index=episode_index,
            seed=seed,
            solved=solved,
            reward=reward,
            truncated=truncated,
            done_reason=done_reason,
            steps_taken=steps_taken,
            invalid_actions=invalid_actions,
            remaining_budget=transition.remaining_budget,
        ),
        steps=step_records,
    )


def summarize(results: list[EpisodeResult]) -> dict[str, Any]:
    total = len(results)
    solved = sum(1 for result in results if result.solved)
    truncated = sum(1 for result in results if result.truncated)
    avg_steps = sum(result.steps_taken for result in results) / total if total else 0.0
    avg_reward = sum(result.reward for result in results) / total if total else 0.0
    return {
        "episodes": total,
        "solve_rate": solved / total if total else 0.0,
        "truncation_rate": truncated / total if total else 0.0,
        "average_steps": avg_steps,
        "average_reward": avg_reward,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run random-policy rollouts over ARC-AGI 3 example games.")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS_PATH)
    parser.add_argument("--episodes-per-task", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=512)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--recordings-dir", type=Path, default=None)
    args = parser.parse_args()

    task_specs = load_task_specs(args.tasks, default_game_factory="arcengine_example:complex_maze")
    results: list[EpisodeResult] = []

    for task_offset, task_spec in enumerate(task_specs):
        for episode_index in range(args.episodes_per_task):
            episode_seed = args.seed + task_offset * 10_000 + episode_index
            artifacts = run_episode(
                task_spec,
                seed=episode_seed,
                episode_index=episode_index,
                max_steps=args.max_steps,
            )
            results.append(artifacts.result)
            if args.recordings_dir is not None:
                _write_recording(
                    recordings_dir=args.recordings_dir,
                    task_spec=task_spec,
                    artifacts=artifacts,
                )

    summary = summarize(results)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(asdict(result), separators=(",", ":")) + "\n")
        summary_path = args.output.with_name(args.output.stem + "_summary.json")
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


def _step_record(*, step_index: int, transition: Transition) -> StepRecord:
    return StepRecord(
        step_index=step_index,
        record_data=transition.record_data,
        step_consumed=transition.step_consumed,
        invalid_action=transition.invalid_action,
        invalid_reason=transition.invalid_reason,
        solved=transition.solved,
        truncated=transition.truncated,
        done=transition.done,
        done_reason=transition.done_reason,
        remaining_budget=transition.remaining_budget,
        frame_count=len(transition.frames),
        frames=transition.frames,
    )


def _write_recording(*, recordings_dir: Path, task_spec: dict[str, Any], artifacts: EpisodeArtifacts) -> None:
    recordings_dir.mkdir(parents=True, exist_ok=True)
    result = artifacts.result
    guid = uuid.uuid4().hex
    filename = f"{task_spec['task_id']}.{guid}.recording.jsonl"
    path = recordings_dir / filename
    with path.open("w", encoding="utf-8") as handle:
        for step in artifacts.steps:
            if step.record_data is None:
                continue
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": step.record_data,
            }
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
