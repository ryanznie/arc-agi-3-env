from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_DIR = ROOT_DIR / "environments" / "arc_agi_3_env"
RECORDINGS_DIR = ROOT_DIR / "evals" / "recordings"

load_dotenv(ROOT_DIR / ".env", override=False)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_record(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        json.dump({"timestamp": _timestamp(), "data": data}, handle)
        handle.write("\n")


def _message_to_dict(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return dict(message.model_dump())
    return dict(message)


def _chat_completion(*, model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    if model == "random":
        return _random_completion(messages=messages)

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    message = data["choices"][0]["message"]
    return {"role": "assistant", "content": message.get("content", "") or ""}


def _extract_available_actions(text: str) -> list[str]:
    marker = "available_actions:"
    for line in text.splitlines():
        if line.startswith(marker):
            raw = line[len(marker) :].strip()
            actions: list[str] = []
            for item in raw.split(","):
                name = item.strip().split("(")[0].strip()
                if name:
                    actions.append(name)
            return actions
    return ["RESET", "ACTION1", "ACTION2", "ACTION3", "ACTION4"]


def _random_completion(*, messages: list[dict[str, Any]]) -> dict[str, Any]:
    latest_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    if latest_user is None:
        return {"role": "assistant", "content": "<action>RESET</action>"}

    content = str(latest_user.get("content", ""))
    if "game_id:" not in content:
        return {"role": "assistant", "content": "<action>RESET</action>"}

    available_actions = _extract_available_actions(content)
    directional_actions = [action for action in available_actions if action in {"ACTION1", "ACTION2", "ACTION3", "ACTION4"}]
    if directional_actions:
        action = random.choice(directional_actions)
        return {"role": "assistant", "content": f"<action>{action}</action>"}

    if "ACTION6" in available_actions:
        return {"role": "assistant", "content": "<action>ACTION6</action><x>0</x><y>0</y>"}

    candidates = [action for action in available_actions if action != "RESET"]
    if not candidates:
        candidates = ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]
    action = random.choice(candidates)
    return {"role": "assistant", "content": f"<action>{action}</action>"}


async def _run(args: argparse.Namespace) -> Path:
    import sys

    sys.path.insert(0, str(ENV_DIR))
    from arc_agi_3_env import load_environment, num_actions, reward, timed_out

    env = load_environment(
        game_family=args.game_family,
        level_index=args.level_index,
        max_turns=args.max_turns,
        game_id=args.game_id,
    )
    row = env.dataset[0]
    state: dict[str, Any] = {"info": row["info"]}
    messages = [_message_to_dict(message) for message in row["prompt"]]

    guid = str(uuid.uuid4())
    prefix = f"{args.game_family}.{args.model}.1"
    recording_path = RECORDINGS_DIR / f"{prefix}.{guid}.recording.jsonl"

    _append_record(
        recording_path,
        {
            "type": "metadata",
            "model": args.model,
            "game_family": args.game_family,
            "level_index": args.level_index,
            "max_turns": args.max_turns,
            "game_id": args.game_id,
            "recording_path": str(recording_path),
        },
    )

    for prompt_message in messages:
        _append_record(recording_path, {"type": "message", "message": prompt_message})

    while True:
        assistant_message = _chat_completion(model=args.model, messages=messages)
        messages.append(assistant_message)
        _append_record(recording_path, {"type": "message", "message": assistant_message})

        env_messages = await env.env_response(messages, state)
        for env_message in env_messages:
            env_message_dict = _message_to_dict(env_message)
            messages.append(env_message_dict)
            _append_record(recording_path, {"type": "message", "message": env_message_dict})

        max_turns_reached = int(state.get("agent_turns", 0)) >= int(args.max_turns)
        if max_turns_reached or await env.is_completed(state):
            break

    _append_record(
        recording_path,
        {
            "type": "summary",
            "reward": reward(state),
            "num_actions": num_actions(state),
            "timed_out": timed_out(state),
            "game_state": state.get("game_state"),
            "agent_turns": state.get("agent_turns"),
        },
    )

    return recording_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a recorded ARC environment eval")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--game-family", default="simple_maze")
    parser.add_argument("--level-index", type=int, default=0)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--game-id", default=None)
    args = parser.parse_args()

    recording_path = asyncio.run(_run(args))
    print(recording_path)


if __name__ == "__main__":
    main()
