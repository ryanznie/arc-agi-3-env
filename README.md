# arc-agi-3-env

PrimeIntellect / Verifiers environment package for ARC-AGI 3 style interactive tasks.

This repo is intentionally thin:
- `arc_agi_3_env.py` exposes `load_environment()`
- `arc_agi_3_env_helpers/` contains action parsing, task loading, engine/session adapters, and formatting helpers
- `tasks/` contains sample task specs

## How It Relates To ARCEngine

`ARCEngine` is the underlying game engine. Per the engine README:
- a game subclasses `ARCBaseGame`
- game logic lives in `step()`
- actions are executed through `perform_action(ActionInput(...))`
- observations come from the camera render path as a 64x64 palette-index grid
- `GameAction.ACTION1` to `ACTION4` conventionally map to up/down/left/right
- `ACTION5` is the contextual "space bar" action
- `ACTION6` is a click action with `x,y` in `[0, 63]`
- `ACTION7` is undo

This repo does not replace that engine. It wraps an `ARCEngine` game into a Prime / Verifiers multi-turn environment so a model can iteratively observe, act, and be scored.

The default task spec now uses a real game from `ARCEngine/examples`, specifically `complex_maze.py`.

## Install

### Local development setup

This assumes the sibling repo layout:

```text
Desktop/work/
  ARCEngine/
  arc-agi-3-env/
```

```bash
cd /Users/ryanznie/Desktop/work/arc-agi-3-env
uv sync
```

This creates `.venv`, installs this package, and installs the declared runtime dependencies such as `arcengine`, `datasets`, and `verifiers`.

If you want to work directly against the sibling `ARCEngine` checkout instead of the released `arcengine` package, reinstall it into the synced environment:

```bash
uv pip install -e ../ARCEngine
```

### Smoke test

This verifies the package imports and that an `ARCEngine/examples` game can reset and step:

```bash
uv run python - <<'PY'
from arc_agi_3_env_helpers.factory import load_factory
from arcengine import ActionInput, GameAction

game_cls = load_factory("arcengine_example:complex_maze")
game = game_cls()
game.full_reset()
frame = game.perform_action(ActionInput(id=GameAction.ACTION4), raw=False)
print(frame.state)
print(len(frame.frame))
PY
```

### Prime local eval

```bash
uv run prime eval run . -m gpt-5-nano -n 1
```

### Local random baseline

This runs random rollouts over the bundled example-game manifest and prints aggregate metrics:

```bash
uv run python -m rl.random_runner --tasks evals/example_games.json --episodes-per-task 3
```

To also save per-episode JSONL plus a summary JSON:

```bash
uv run python -m rl.random_runner \
  --tasks evals/example_games.json \
  --episodes-per-task 3 \
  --output evals/random_results.jsonl
```

To save full per-step recordings sourced from ARCEngine's returned frames:

```bash
uv run python -m rl.random_runner \
  --tasks evals/example_games.json \
  --episodes-per-task 1 \
  --output evals/random_results.jsonl \
  --recordings-dir recordings
```

## Notes

- The default environment uses a real example game from `ARCEngine/examples`.
- The custom factory path format `arcengine_example:<name>` currently supports `simple_maze`, `complex_maze`, `merge`, and `merge_detach`.
- The local random baseline samples uniformly from the game's valid action set when available.
- Saved recordings use the canonical `<prefix>.<guid>.recording.jsonl` pattern in `recordings/`, with one JSON event per line shaped like the existing recorder: `{"timestamp": ..., "data": ...}`.
- The current prompt format sends the 64x64 observation as compact JSON. That is simple and model-agnostic, but not token-efficient.
- `load_environment()` imports `verifiers` lazily, so the module itself can still be imported before the Prime runtime dependencies are installed.
