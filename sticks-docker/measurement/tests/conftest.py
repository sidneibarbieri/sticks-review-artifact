from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "sticks-docker"
MEASUREMENT_ROOT = PACKAGE_ROOT / "measurement"
SCRIPTS_ROOT = MEASUREMENT_ROOT / "scripts"


def _register_namespace(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module


def _load_module(module_name: str, path: Path) -> None:
    if module_name in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


_register_namespace("sticks_docker", PACKAGE_ROOT)
_register_namespace("sticks_docker.measurement", MEASUREMENT_ROOT)
_register_namespace("sticks_docker.measurement.scripts", SCRIPTS_ROOT)
_load_module(
    "sticks_docker.measurement.scripts.run_curated_caldera_campaigns",
    SCRIPTS_ROOT / "run_curated_caldera_campaigns.py",
)
_load_module(
    "sticks_docker.measurement.scripts.prepare_docker_runtime_context",
    SCRIPTS_ROOT / "prepare_docker_runtime_context.py",
)
_load_module(
    "sticks_docker.measurement.scripts.capture_docker_operation_plateau",
    SCRIPTS_ROOT / "capture_docker_operation_plateau.py",
)
