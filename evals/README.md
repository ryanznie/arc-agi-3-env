# Evals

## Local Smoke Test

Run the simplest end-to-end eval against `simple_maze` level 0:

```bash
set -a
source .env
set +a
cd environments/arc_agi_3_env
PYTHONPATH="$PWD" uv run vf-eval arc-agi-3-env \
  -m gpt-4.1-mini \
  -b https://api.openai.com/v1 \
  -k OPENAI_API_KEY \
  -a '{"game_family":"simple_maze","level_index":0,"max_turns":8}' \
  -n 1 -r 1
```

This is the supported path because the current `verifiers` worker import path still needs `PYTHONPATH` set explicitly for this local environment.

## Recording Run

If you want an ARC-style `.recording.jsonl`, use:

```bash
uv run --project environments/arc_agi_3_env python evals/run_recording.py \
  --game-family simple_maze \
  --level-index 0 \
  --max-turns 8
```

To test without calling OpenAI, use the built-in random policy:

```bash
uv run --project environments/arc_agi_3_env python evals/run_recording.py \
  --model random \
  --game-family simple_maze \
  --level-index 0 \
  --max-turns 8
```

This writes a file under `evals/recordings/` such as:

```text
evals/recordings/simple_maze.gpt-4.1-mini.1.<guid>.recording.jsonl
```

The file contains:
- initial prompt messages
- each assistant action
- each environment response
- a final summary event with `reward`, `num_actions`, and `timed_out`

Example summary from a recent `simple_maze` run:

```json
{"type":"summary","reward":0.0,"num_actions":7.0,"timed_out":1.0,"game_state":"NOT_FINISHED","agent_turns":8}
```

## Equivalent Manual Command

```bash
set -a
source .env
set +a
cd environments/arc_agi_3_env
PYTHONPATH="$PWD" uv run vf-eval arc-agi-3-env \
  -m gpt-4.1-mini \
  -b https://api.openai.com/v1 \
  -k OPENAI_API_KEY \
  -a '{"game_family":"simple_maze","level_index":0,"max_turns":8}' \
  -n 1 \
  -r 1
```

## ARC-AGI Remote Eval

After the local smoke test works, switch the env args:

```bash
set -a
source .env
set +a
cd environments/arc_agi_3_env
PYTHONPATH="$PWD" uv run vf-eval arc-agi-3-env \
  -m gpt-4.1-mini \
  -b https://api.openai.com/v1 \
  -k OPENAI_API_KEY \
  -a '{"game_family":"arc_agi","max_turns":8}' \
  -n 1 \
  -r 1
```

For ARC-AGI click tasks, the environment expects XML like:

```xml
<action>ACTION6</action><x>12</x><y>34</y>
```

## Select A Specific ARC-AGI Puzzle

List available ARC-AGI puzzle ids:

```bash
set -a
source .env
set +a

python - <<'PY'
import os, requests
r = requests.get(
    f"{os.environ['ROOT_URL'].rstrip('/')}/api/games",
    headers={"X-API-Key": os.environ["ARC_API_KEY"], "Accept": "application/json"},
    timeout=30,
)
r.raise_for_status()
for item in r.json():
    print(item["game_id"])
PY
```

Record one specific puzzle:

```bash
set -a
source .env
set +a

uv run --project environments/arc_agi_3_env python evals/run_recording.py \
  --game-family arc_agi \
  --game-id ft09-0d8bbf25 \
  --max-turns 3
```

Run `vf-eval` on one specific puzzle:

```bash
set -a
source .env
set +a
cd environments/arc_agi_3_env
PYTHONPATH="$PWD" uv run vf-eval arc-agi-3-env \
  -m gpt-4.1-mini \
  -b https://api.openai.com/v1 \
  -k OPENAI_API_KEY \
  -a '{"game_family":"arc_agi","game_id":"ft09-0d8bbf25","max_turns":3}' \
  -n 1 \
  -r 1
```
