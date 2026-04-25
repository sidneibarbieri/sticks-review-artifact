#!/usr/bin/env python3
"""
Capture a stable Caldera operation plateau for the STICKS Docker artifact.

This script does not create operations. It observes the current Caldera API,
waits until the operation fingerprint remains stable for a configurable number
of polls, and then writes a measurement snapshot using the same output schema
as run_curated_caldera_campaigns.py.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any


MEASUREMENT_ROOT = Path(__file__).resolve().parent.parent
SIBLING_RUNNER = Path(__file__).resolve().parent / "run_curated_caldera_campaigns.py"


def load_runner_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_curated_caldera_campaigns",
        SIBLING_RUNNER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load runner module from {SIBLING_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def wait_for_plateau(
    runner: ModuleType,
    base_url: str,
    api_key: str,
    stable_polls: int,
    poll_interval_seconds: int,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_seconds
    previous_fingerprint: tuple[tuple[Any, ...], ...] | None = None
    stable_matches = 0
    last_operations: list[dict[str, Any]] = []
    while time.time() < deadline:
        last_operations = runner.api_get_json(base_url, api_key, "/api/v2/operations")
        current_fingerprint = runner.operations_fingerprint(last_operations)
        if runner.operations_are_quiescent(last_operations, previous_fingerprint):
            stable_matches += 1
            if stable_matches >= stable_polls:
                return last_operations
        else:
            stable_matches = 0
        previous_fingerprint = current_fingerprint
        time.sleep(poll_interval_seconds)
    raise TimeoutError(
        f"Operations did not reach a stable plateau within {timeout_seconds} seconds."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caldera-url", default="http://127.0.0.1:8888")
    parser.add_argument("--api-key", default="ADMIN123")
    parser.add_argument("--group", default="red")
    parser.add_argument("--stable-polls", type=int, default=6)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=600)
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()
    runner = load_runner_module()
    agents = runner.api_get_json(arguments.caldera_url, arguments.api_key, "/api/v2/agents")
    operations = wait_for_plateau(
        runner,
        arguments.caldera_url,
        arguments.api_key,
        stable_polls=arguments.stable_polls,
        poll_interval_seconds=arguments.poll_interval,
        timeout_seconds=arguments.timeout,
    )
    artifacts = runner.list_curated_artifacts()
    payload = {
        "generated_at_utc": runner.utc_now_iso(),
        "capture_mode": "plateau_probe",
        "notes": [
            "Operations reached a stable non-terminal plateau under one compose-managed red agent.",
            "Snapshot captured directly from the Caldera API after a stable-fingerprint probe.",
        ],
        "caldera_url": arguments.caldera_url,
        "group": arguments.group,
        "poll_timeout_reached": False,
        "quiescent_plateau_reached": True,
        "effective_quiescent_seconds": arguments.stable_polls * arguments.poll_interval,
        "counts": {
            "curated_abilities": sum(1 for artifact in artifacts if artifact.kind == "ability"),
            "curated_adversaries": sum(1 for artifact in artifacts if artifact.kind == "adversary"),
            "red_agents": len([agent for agent in agents if agent.get("group") == arguments.group]),
            "operations": len(operations),
        },
        "agents": agents,
        "artifacts": [
            {
                "kind": artifact.kind,
                "path": runner.display_path(artifact.path),
                "name": artifact.name,
            }
            for artifact in artifacts
        ],
        "empty_caldera": {"stdout": "captured after clean rerun", "stderr": ""},
        "load_log": [],
        "operation_creation": {"stdout": "captured after clean rerun", "stderr": ""},
        "operations": runner.summarize_operations(operations),
    }
    json_path, md_path = runner.write_results(payload)
    print(f"Wrote JSON summary to {json_path}")
    print(f"Wrote Markdown summary to {md_path}")


if __name__ == "__main__":
    main()
