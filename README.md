# arc-agi-3-env

PrimeIntellect / Verifiers environment for ARC-style games using `arcengine`, with:
- local `simple_maze`
- local `complex_maze`
- remote `arc_agi` tasks via `ARC_API_KEY` + `ROOT_URL`

## Setup

Fill in [.env](/Users/ryanznie/Desktop/work/arc-agi-3-env/.env):

```bash
ARC_API_KEY=...
ROOT_URL=https://three.arcprize.org
OPENAI_API_KEY=...
```

The environment module loads `.env` automatically.

## Quick Test

Run the local smoke eval:

```bash
set -a
source .env
set +a
PYTHONPATH=environments/arc_agi_3_env uv run --project environments/arc_agi_3_env vf-eval arc-agi-3-env \
  -m gpt-4.1-mini \
  -b https://api.openai.com/v1 \
  -k OPENAI_API_KEY \
  -a '{"game_family":"simple_maze","level_index":0,"max_turns":8}' \
  -n 1 -r 1
```

Generate an ARC-style `.recording.jsonl`:

```bash
uv run --project environments/arc_agi_3_env python environments/arc_agi_3_env/evals/run_recording.py \
  --game-family simple_maze \
  --level-index 0 \
  --max-turns 8
```

Run a specific ARC-AGI puzzle by id:

```bash
set -a
source .env
set +a

uv run --project environments/arc_agi_3_env python environments/arc_agi_3_env/evals/run_recording.py \
  --game-family arc_agi \
  --game-id ft09-0d8bbf25 \
  --max-turns 3
```

See:
- [environment README](/Users/ryanznie/Desktop/work/arc-agi-3-env/environments/arc_agi_3_env/README.md)
- [evals README](/Users/ryanznie/Desktop/work/arc-agi-3-env/environments/arc_agi_3_env/evals/README.md)
