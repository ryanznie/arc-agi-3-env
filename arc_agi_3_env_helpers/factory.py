from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable


def load_factory(factory_path: str) -> Callable[..., Any]:
    if factory_path.startswith("arcengine_example:"):
        example_name = factory_path.split(":", 1)[1]
        return _load_arcengine_example_factory(example_name)

    module_name, _, attr_name = factory_path.partition(":")
    if not module_name or not attr_name:
        raise ValueError(f"Factory path must be '<module>:<callable>', got: {factory_path!r}")

    module = importlib.import_module(module_name)
    factory = getattr(module, attr_name, None)
    if factory is None or not callable(factory):
        raise ValueError(f"Factory '{factory_path}' was not found or is not callable.")
    return factory


def _load_arcengine_example_factory(example_name: str) -> Callable[..., Any]:
    examples_dir = Path(__file__).resolve().parents[2] / "ARCEngine" / "examples"
    module_path = examples_dir / f"{example_name}.py"
    if not module_path.exists():
        raise ValueError(f"Unknown ARCEngine example '{example_name}'. Expected file at {module_path}.")

    if str(examples_dir) not in sys.path:
        sys.path.insert(0, str(examples_dir))

    module_name = f"arcengine_examples_{example_name}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load module spec for example '{example_name}'.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    class_name = _example_class_name(example_name)
    factory = getattr(module, class_name, None)
    if factory is None or not callable(factory):
        raise ValueError(f"Example '{example_name}' did not expose callable class '{class_name}'.")
    return factory


def _example_class_name(example_name: str) -> str:
    if example_name == "simple_maze":
        return "SimpleMaze"
    if example_name == "complex_maze":
        return "ComplexMaze"
    if example_name == "merge":
        return "Merge"
    if example_name == "merge_detach":
        return "MergeDetatch"
    raise ValueError(f"Unsupported ARCEngine example '{example_name}'.")
