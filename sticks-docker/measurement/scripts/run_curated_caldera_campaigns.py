#!/usr/bin/env python3
"""
Execute the frozen STICKS Docker Stage 3 workflow and capture a measurement
summary.

This script intentionally orchestrates the existing tools under
sticks-docker/sticks/ instead of re-implementing their semantics. The Docker
artifact remains frozen; new measurement logic lives only in the measurement
boundary.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


MEASUREMENT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = MEASUREMENT_ROOT.parent.parent
STICKS_DOCKER_ROOT = WORKSPACE_ROOT / "sticks-docker"
FROZEN_STICKS_ROOT = STICKS_DOCKER_ROOT / "sticks"
CURATED_API_DIR = FROZEN_STICKS_ROOT / "data" / "api"
DEFAULT_RUNTIME_API_DIR = MEASUREMENT_ROOT / "runtime" / "curated-api"
RESULTS_DIR = MEASUREMENT_ROOT / "results"
LATEST_JSON = RESULTS_DIR / "docker_caldera_execution_latest.json"
LATEST_MD = RESULTS_DIR / "DOCKER_CALDERA_EXECUTION_LATEST.md"

DEFAULT_CALDERA_URL = "http://127.0.0.1:8888"
DEFAULT_API_KEY = "ADMIN123"
DEFAULT_GROUP = "red"
DEFAULT_AGENT_TIMEOUT = 300
DEFAULT_OPERATION_TIMEOUT = 2400
DEFAULT_POLL_INTERVAL = 5
DEFAULT_QUIESCENT_SECONDS = 120
DEFAULT_SUBSTRATE_TIMEOUT = 900
DEFAULT_SUBSTRATE_POLL_INTERVAL = 5
DEFAULT_IMPORT_RETRIES = 3
DEFAULT_IMPORT_RETRY_DELAY = 5
TERMINAL_OPERATION_STATES = {
    "finished",
    "completed",
    "cleanup",
    "out_of_time",
    "timed_out",
    "paused",
}
SUBSTRATE_PORT_REQUIREMENTS = {
    "nginx": (22, 5055, 8080, 8116),
    "db": (22, 80),
}


def display_path(path: Path) -> str:
    path = path.resolve()
    for root in (WORKSPACE_ROOT, MEASUREMENT_ROOT):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            pass
    for marker in ("curated-api", "docker-context", "sticks-docker", "results"):
        if marker in path.parts:
            index = path.parts.index(marker)
            return Path(*path.parts[index:]).as_posix()
    return path.name or path.as_posix()


@dataclass(frozen=True)
class CuratedArtifact:
    path: Path
    kind: str
    name: str


@dataclass(frozen=True)
class OperationCreationResult:
    stdout: str
    stderr: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_headers(api_key: str) -> dict[str, str]:
    return {"KEY": api_key, "Content-Type": "application/json"}


def api_get_json(base_url: str, api_key: str, endpoint: str) -> Any:
    response = requests.get(
        f"{base_url.rstrip('/')}{endpoint}",
        headers=build_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def wait_for_caldera(base_url: str, api_key: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            api_get_json(base_url, api_key, "/api/v2/agents")
            return
        except requests.RequestException:
            time.sleep(2)
    raise TimeoutError(
        f"Caldera API at {base_url} did not become ready within {timeout_seconds} seconds."
    )


def wait_for_group_agent(
    base_url: str,
    api_key: str,
    group_name: str,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        agents = api_get_json(base_url, api_key, "/api/v2/agents")
        matching_agents = [agent for agent in agents if agent.get("group") == group_name]
        ready_agents = [
            agent
            for agent in matching_agents
            if agent.get("trusted") is True
            and str(agent.get("contact", "")).lower() != "unknown"
            and str(agent.get("pending_contact", "")).lower() != "unknown"
        ]
        if ready_agents:
            return ready_agents
        time.sleep(2)
    raise TimeoutError(
        "No trusted, operation-ready agents joined "
        f"group '{group_name}' within {timeout_seconds} seconds."
    )


def resolve_curated_api_dir(explicit_dir: Path | None = None) -> Path:
    if explicit_dir is not None:
        return explicit_dir
    if DEFAULT_RUNTIME_API_DIR.exists():
        return DEFAULT_RUNTIME_API_DIR
    return CURATED_API_DIR


def list_curated_artifacts(curated_api_dir: Path | None = None) -> list[CuratedArtifact]:
    api_root = resolve_curated_api_dir(curated_api_dir)
    artifacts: list[CuratedArtifact] = []
    for path in sorted(api_root.glob("*.json")):
        lower_name = path.name.lower()
        if "adversary" in lower_name:
            kind = "adversary"
        elif "ability" in lower_name:
            kind = "ability"
        else:
            continue
        artifacts.append(CuratedArtifact(path=path, kind=kind, name=path.name))
    return artifacts


def artifact_campaign_key(artifact: CuratedArtifact) -> str:
    if artifact.name.endswith("_dag-ability.json"):
        return artifact.name.removesuffix("_dag-ability.json")
    if artifact.name.endswith("_dag-adversary.json"):
        return artifact.name.removesuffix("_dag-adversary.json")
    raise ValueError(f"Unsupported curated artifact name: {artifact.name}")


def filter_artifacts_by_adversary_names(
    artifacts: list[CuratedArtifact],
    selected_names: list[str],
) -> list[CuratedArtifact]:
    requested_names = [name.strip() for name in selected_names if name.strip()]
    if not requested_names:
        return artifacts

    name_to_campaign_key: dict[str, str] = {}
    for artifact in artifacts:
        if artifact.kind != "adversary":
            continue
        payload = load_artifact_payloads(artifact.path)[0]
        adversary_name = str(payload.get("name", "")).strip()
        if not adversary_name:
            raise ValueError(f"Curated adversary artifact has no name: {artifact.path}")
        name_to_campaign_key[adversary_name] = artifact_campaign_key(artifact)

    missing_names = sorted(set(requested_names) - set(name_to_campaign_key))
    if missing_names:
        available_names = ", ".join(sorted(name_to_campaign_key))
        missing_display = ", ".join(missing_names)
        raise ValueError(
            "Unknown curated adversary name(s): "
            f"{missing_display}. Available names: {available_names}"
        )

    selected_campaign_keys = {
        name_to_campaign_key[requested_name] for requested_name in requested_names
    }
    return [
        artifact
        for artifact in artifacts
        if artifact_campaign_key(artifact) in selected_campaign_keys
    ]


def run_host_tool(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        capture_output=True,
        text=True,
        check=False,
    )


def delete_all_objects(
    base_url: str,
    api_key: str,
    endpoint: str,
    id_field: str,
) -> dict[str, int]:
    objects = api_get_json(base_url, api_key, endpoint)
    deleted = 0
    for obj in objects:
        identifier = obj.get(id_field)
        if not identifier:
            continue
        response = requests.delete(
            f"{base_url.rstrip('/')}{endpoint}/{identifier}",
            headers=build_headers(api_key),
            timeout=30,
        )
        response.raise_for_status()
        deleted += 1
    remaining = api_get_json(base_url, api_key, endpoint)
    if remaining:
        raise RuntimeError(
            f"Caldera cleanup failed for {endpoint}: {len(remaining)} objects remain."
    )
    return {"deleted": deleted, "remaining": len(remaining)}


def delete_matching_objects(
    base_url: str,
    api_key: str,
    endpoint: str,
    id_field: str,
    identifiers: set[str],
) -> dict[str, int]:
    if not identifiers:
        return {"deleted": 0, "remaining": 0}
    objects = api_get_json(base_url, api_key, endpoint)
    deleted = 0
    for obj in objects:
        identifier = obj.get(id_field)
        if not identifier or str(identifier) not in identifiers:
            continue
        response = requests.delete(
            f"{base_url.rstrip('/')}{endpoint}/{identifier}",
            headers=build_headers(api_key),
            timeout=30,
        )
        response.raise_for_status()
        deleted += 1
    remaining = api_get_json(base_url, api_key, endpoint)
    remaining_matches = sum(
        1 for obj in remaining if str(obj.get(id_field, "")) in identifiers
    )
    if remaining_matches:
        raise RuntimeError(
            f"Caldera cleanup failed for {endpoint}: "
            f"{remaining_matches} curated objects remain."
        )
    return {"deleted": deleted, "remaining": remaining_matches}


def build_container_port_check_command(container_name: str, ports: tuple[int, ...]) -> list[str]:
    probes = " && ".join(f"ss -tuln | grep -q ':{port} '" for port in ports)
    return ["docker", "exec", container_name, "sh", "-lc", probes]


def container_ports_ready(container_name: str, ports: tuple[int, ...]) -> bool:
    completed = run_host_tool(build_container_port_check_command(container_name, ports))
    return completed.returncode == 0


def wait_for_shared_substrate(
    timeout_seconds: int,
    poll_interval_seconds: int,
) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if all(
            container_ports_ready(container_name, ports)
            for container_name, ports in SUBSTRATE_PORT_REQUIREMENTS.items()
        ):
            return
        time.sleep(poll_interval_seconds)
    raise TimeoutError(
        "Docker shared substrate did not expose all required campaign services "
        f"within {timeout_seconds} seconds."
    )


def load_artifact_payloads(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return [payload]


def import_curated_object(
    base_url: str,
    api_key: str,
    endpoint: str,
    payload: dict[str, Any],
    retries: int,
    retry_delay_seconds: int,
) -> requests.Response:
    last_error: Exception | None = None
    last_response: requests.Response | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                f"{base_url.rstrip('/')}{endpoint}",
                headers=build_headers(api_key),
                json=payload,
                timeout=30,
            )
            if response.status_code == 200:
                return response
            last_response = response
        except requests.RequestException as error:
            last_error = error
        if attempt < retries:
            time.sleep(retry_delay_seconds)
    if last_response is not None:
        raise RuntimeError(
            f"Failed to import curated object into {endpoint}: "
            f"{last_response.status_code} - {last_response.text}"
        )
    if last_error is not None:
        raise RuntimeError(
            f"Failed to import curated object into {endpoint}: {last_error}"
        ) from last_error
    raise RuntimeError(f"Failed to import curated object into {endpoint}.")


def load_curated_artifacts(
    base_url: str,
    api_key: str,
    artifacts: list[CuratedArtifact],
    retries: int = DEFAULT_IMPORT_RETRIES,
    retry_delay_seconds: int = DEFAULT_IMPORT_RETRY_DELAY,
) -> list[dict[str, str]]:
    execution_log: list[dict[str, str]] = []
    for artifact in artifacts:
        endpoint = "/api/v2/adversaries" if artifact.kind == "adversary" else "/api/v2/abilities"
        for payload in load_artifact_payloads(artifact.path):
            response = import_curated_object(
                base_url,
                api_key,
                endpoint,
                payload,
                retries=retries,
                retry_delay_seconds=retry_delay_seconds,
            )
            execution_log.append(
                {
                    "kind": artifact.kind,
                    "path": display_path(artifact.path),
                    "endpoint": endpoint,
                    "object_id": str(
                        payload.get("adversary_id")
                        or payload.get("ability_id")
                        or payload.get("id")
                        or payload.get("name")
                    ),
                    "stdout": response.text.strip(),
                    "stderr": "",
                }
            )
    return execution_log


def delete_matching_adversaries_by_name(
    base_url: str,
    api_key: str,
    names: set[str],
) -> dict[str, int]:
    if not names:
        return {"deleted": 0, "remaining": 0}
    adversaries = api_get_json(base_url, api_key, "/api/v2/adversaries")
    deleted = 0
    for adversary in adversaries:
        if str(adversary.get("name", "")) not in names:
            continue
        adversary_id = adversary.get("adversary_id")
        if not adversary_id:
            continue
        response = requests.delete(
            f"{base_url.rstrip('/')}/api/v2/adversaries/{adversary_id}",
            headers=build_headers(api_key),
            timeout=30,
        )
        response.raise_for_status()
        deleted += 1
    remaining = api_get_json(base_url, api_key, "/api/v2/adversaries")
    remaining_matches = sum(
        1 for adversary in remaining if str(adversary.get("name", "")) in names
    )
    if remaining_matches:
        raise RuntimeError(
            f"Caldera cleanup failed for /api/v2/adversaries: "
            f"{remaining_matches} curated adversaries remain."
        )
    return {"deleted": deleted, "remaining": remaining_matches}


def create_operation(
    base_url: str,
    api_key: str,
    operation_name: str,
    group_name: str,
    adversary_id: str,
) -> OperationCreationResult:
    payload = {
        "index": "operations",
        "name": operation_name,
        "group": group_name,
        "planner": "atomic",
        "jitter": "2/8",
        "adversary_id": adversary_id,
    }
    response = requests.put(
        f"{base_url.rstrip('/')}/api/rest",
        headers=build_headers(api_key),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return OperationCreationResult(stdout=response.text.strip())


def collect_curated_object_ids(artifacts: list[CuratedArtifact]) -> dict[str, set[str]]:
    ability_ids: set[str] = set()
    adversary_names: set[str] = set()
    for artifact in artifacts:
        for payload in load_artifact_payloads(artifact.path):
            if artifact.kind == "ability":
                identifier = payload.get("ability_id") or payload.get("id")
                if identifier:
                    ability_ids.add(str(identifier))
            elif artifact.kind == "adversary":
                identifier = payload.get("name")
                if identifier:
                    adversary_names.add(str(identifier))
    return {"abilities": ability_ids, "adversaries": adversary_names}


def extract_loaded_adversaries(
    artifacts: list[CuratedArtifact],
    load_log: list[dict[str, str]],
) -> list[dict[str, str]]:
    load_log_by_path = {
        entry["path"]: entry for entry in load_log if entry.get("kind") == "adversary"
    }
    loaded_adversaries: list[dict[str, str]] = []
    for artifact in artifacts:
        if artifact.kind != "adversary":
            continue
        entry = load_log_by_path.get(display_path(artifact.path))
        if entry is None:
            entry = load_log_by_path[str(artifact.path)]
        payload = json.loads(entry["stdout"])
        loaded_adversaries.append(
            {
                "name": str(payload["name"]),
                "adversary_id": str(payload["adversary_id"]),
            }
        )
    return loaded_adversaries


def create_curated_operations(
    loaded_adversaries: list[dict[str, str]],
    group_name: str,
    base_url: str,
    api_key: str,
) -> list[dict[str, str]]:
    creation_log: list[dict[str, str]] = []
    for index, adversary in enumerate(loaded_adversaries, start=1):
        operation_name = f"OP{index:03d}"
        completed = create_operation(
            base_url=base_url,
            api_key=api_key,
            operation_name=operation_name,
            group_name=group_name,
            adversary_id=adversary["adversary_id"],
        )
        creation_log.append(
            {
                "operation_name": operation_name,
                "adversary_name": adversary["name"],
                "adversary_id": adversary["adversary_id"],
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )
    return creation_log


def empty_caldera(
    base_url: str,
    api_key: str,
    artifacts: list[CuratedArtifact] | None = None,
) -> dict[str, dict[str, int]]:
    if artifacts is None:
        return {
            "operations": delete_all_objects(base_url, api_key, "/api/v2/operations", "id"),
            "adversaries": delete_matching_adversaries_by_name(
                base_url,
                api_key,
                set(),
            ),
            "abilities": delete_all_objects(
                base_url, api_key, "/api/v2/abilities", "ability_id"
            ),
        }
    curated_ids = collect_curated_object_ids(artifacts)
    return {
        "operations": delete_all_objects(base_url, api_key, "/api/v2/operations", "id"),
        "adversaries": delete_matching_adversaries_by_name(
            base_url,
            api_key,
            curated_ids["adversaries"],
        ),
        "abilities": delete_matching_objects(
            base_url,
            api_key,
            "/api/v2/abilities",
            "ability_id",
            curated_ids["abilities"],
        ),
    }


def normalize_step_status(step: dict[str, Any]) -> str:
    if "status" in step and step["status"]:
        return str(step["status"])
    if step.get("run"):
        return "ran"
    if step.get("pid"):
        return "started"
    return "unknown"


def operation_chain_status_counts(operation: dict[str, Any]) -> dict[str, int]:
    chain = operation.get("chain", [])
    status_counts: dict[str, int] = {}
    for link in chain:
        status = str(link.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1
    return status_counts


def operation_last_link_summary(operation: dict[str, Any]) -> dict[str, Any] | None:
    chain = operation.get("chain", [])
    if not chain:
        return None
    last_link = chain[-1]
    ability = last_link.get("ability", {})
    return {
        "status": last_link.get("status"),
        "output": last_link.get("output"),
        "technique_id": ability.get("technique_id"),
        "name": ability.get("name"),
        "command": last_link.get("command"),
    }


def operation_nonzero_links_summary(operation: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for index, link in enumerate(operation.get("chain", []), start=1):
        try:
            status = int(link.get("status", 0))
        except (TypeError, ValueError):
            status = 0
        if status == 0:
            continue
        ability = link.get("ability", {})
        summaries.append(
            {
                "index": index,
                "status": status,
                "output": link.get("output"),
                "technique_id": ability.get("technique_id"),
                "name": ability.get("name"),
                "command": link.get("command"),
            }
        )
    return summaries


def operation_fingerprint(operation: dict[str, Any]) -> tuple[Any, ...]:
    chain = operation.get("chain", [])
    return (
        operation.get("id"),
        operation.get("state"),
        len(chain),
        tuple(link.get("status") for link in chain),
    )


def operations_fingerprint(operations: list[dict[str, Any]]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        operation_fingerprint(operation)
        for operation in sorted(operations, key=lambda item: str(item.get("id")))
    )


def operations_are_quiescent(
    operations: list[dict[str, Any]],
    previous_fingerprint: tuple[tuple[Any, ...], ...] | None,
) -> bool:
    if not operations:
        return False
    current_fingerprint = operations_fingerprint(operations)
    if previous_fingerprint is None:
        return False
    if current_fingerprint != previous_fingerprint:
        return False
    return all(operation.get("chain") for operation in operations)


def summarize_operations(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for operation in operations:
        steps = operation.get("steps", [])
        step_status_counts: dict[str, int] = {}
        for step in steps:
            status = normalize_step_status(step)
            step_status_counts[status] = step_status_counts.get(status, 0) + 1

        summaries.append(
            {
                "id": operation.get("id"),
                "name": operation.get("name"),
                "state": operation.get("state"),
                "planner": operation.get("planner"),
                "adversary": operation.get("adversary", {}),
                "host_group": operation.get("group"),
                "step_count": len(steps),
                "step_status_counts": step_status_counts,
                "chain_count": len(operation.get("chain", [])),
                "chain_status_counts": operation_chain_status_counts(operation),
                "last_link": operation_last_link_summary(operation),
                "nonzero_links": operation_nonzero_links_summary(operation),
            }
        )
    return summaries


def poll_operations(
    base_url: str,
    api_key: str,
    timeout_seconds: int,
    poll_interval_seconds: int,
    quiescent_seconds: int,
) -> tuple[list[dict[str, Any]], bool, bool]:
    deadline = time.time() + timeout_seconds
    last_operations: list[dict[str, Any]] = []
    previous_fingerprint: tuple[tuple[Any, ...], ...] | None = None
    stable_seconds = 0
    while time.time() < deadline:
        last_operations = api_get_json(base_url, api_key, "/api/v2/operations")
        if last_operations and all(
            str(operation.get("state", "")).lower() in TERMINAL_OPERATION_STATES
            for operation in last_operations
        ):
            return last_operations, False, False
        current_fingerprint = operations_fingerprint(last_operations)
        if operations_are_quiescent(last_operations, previous_fingerprint):
            stable_seconds += poll_interval_seconds
            if stable_seconds >= quiescent_seconds:
                return last_operations, False, True
        else:
            stable_seconds = 0
        previous_fingerprint = current_fingerprint
        time.sleep(poll_interval_seconds)
    return last_operations, True, False


def render_markdown_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# Docker Caldera Execution Audit",
        "",
        f"- Generated at: `{payload['generated_at_utc']}`",
        f"- Caldera URL: `{payload['caldera_url']}`",
        f"- Curated abilities loaded: `{payload['counts']['curated_abilities']}`",
        f"- Curated adversaries loaded: `{payload['counts']['curated_adversaries']}`",
        f"- Agents in group `red`: `{payload['counts']['red_agents']}`",
        f"- Operations observed: `{payload['counts']['operations']}`",
        f"- Poll timeout reached: `{payload['poll_timeout_reached']}`",
        f"- Quiescent plateau reached: `{payload['quiescent_plateau_reached']}`",
        f"- Effective quiescent window (s): `{payload['effective_quiescent_seconds']}`",
        "",
        "## Operation States",
        "",
    ]

    for operation in payload["operations"]:
        lines.extend(
            [
                f"### {operation['name']}",
                f"- State: `{operation['state']}`",
                f"- Step count: `{operation['step_count']}`",
                f"- Step status counts: `{json.dumps(operation['step_status_counts'], sort_keys=True)}`",
                f"- Chain count: `{operation['chain_count']}`",
                f"- Chain status counts: `{json.dumps(operation['chain_status_counts'], sort_keys=True)}`",
                "",
            ]
        )
        last_link = operation.get("last_link")
        if last_link:
            lines.extend(
                [
                    f"- Last link status: `{last_link['status']}`",
                    f"- Last link technique: `{last_link['technique_id']}` {last_link['name']}",
                    f"- Last link output: `{last_link['output']}`",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def write_results(
    payload: dict[str, Any],
    update_latest: bool = True,
) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = payload["generated_at_utc"].replace(":", "").replace("-", "")
    json_path = RESULTS_DIR / f"docker_caldera_execution_{timestamp}.json"
    md_path = RESULTS_DIR / f"DOCKER_CALDERA_EXECUTION_{timestamp}.md"
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    md_text = render_markdown_summary(payload)
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    if update_latest:
        LATEST_JSON.write_text(json_text, encoding="utf-8")
        LATEST_MD.write_text(md_text, encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caldera-url", default=DEFAULT_CALDERA_URL)
    parser.add_argument("--api-key", default=DEFAULT_API_KEY)
    parser.add_argument("--group", default=DEFAULT_GROUP)
    parser.add_argument(
        "--curated-api-dir",
        type=Path,
        default=None,
        help="Optional measurement-side curated API overlay directory.",
    )
    parser.add_argument(
        "--adversary-name",
        action="append",
        default=[],
        help=(
            "Optional curated adversary name to run. May be repeated to focus "
            "the batch on a subset of campaigns."
        ),
    )
    parser.add_argument("--agent-timeout", type=int, default=DEFAULT_AGENT_TIMEOUT)
    parser.add_argument("--operation-timeout", type=int, default=DEFAULT_OPERATION_TIMEOUT)
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL)
    parser.add_argument("--quiescent-seconds", type=int, default=DEFAULT_QUIESCENT_SECONDS)
    parser.add_argument("--substrate-timeout", type=int, default=DEFAULT_SUBSTRATE_TIMEOUT)
    parser.add_argument(
        "--substrate-poll-interval",
        type=int,
        default=DEFAULT_SUBSTRATE_POLL_INTERVAL,
    )
    parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Skip emptying Caldera before loading curated artifacts.",
    )
    parser.add_argument(
        "--skip-substrate-wait",
        action="store_true",
        help="Skip waiting for the shared Docker substrate to expose required services.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()

    wait_for_caldera(arguments.caldera_url, arguments.api_key, arguments.agent_timeout)
    agents = wait_for_group_agent(
        arguments.caldera_url,
        arguments.api_key,
        arguments.group,
        arguments.agent_timeout,
    )
    if not arguments.skip_substrate_wait:
        wait_for_shared_substrate(
            timeout_seconds=arguments.substrate_timeout,
            poll_interval_seconds=arguments.substrate_poll_interval,
        )
    effective_quiescent_seconds = max(
        arguments.quiescent_seconds,
        max(int(agent.get("sleep_max", 0)) for agent in agents) * 2,
    )

    curated_api_dir = resolve_curated_api_dir(arguments.curated_api_dir)
    artifacts = filter_artifacts_by_adversary_names(
        list_curated_artifacts(curated_api_dir),
        arguments.adversary_name,
    )
    empty_result: dict[str, dict[str, int]] | None = None
    if not arguments.skip_empty:
        empty_result = empty_caldera(arguments.caldera_url, arguments.api_key, artifacts)
    load_log = load_curated_artifacts(
        arguments.caldera_url,
        arguments.api_key,
        artifacts,
    )
    loaded_adversaries = extract_loaded_adversaries(artifacts, load_log)
    operation_creation = create_curated_operations(
        loaded_adversaries,
        arguments.group,
        arguments.caldera_url,
        arguments.api_key,
    )
    operations, poll_timeout_reached, quiescent_plateau_reached = poll_operations(
        arguments.caldera_url,
        arguments.api_key,
        arguments.operation_timeout,
        arguments.poll_interval,
        effective_quiescent_seconds,
    )

    payload = {
        "generated_at_utc": utc_now_iso(),
        "caldera_url": arguments.caldera_url,
        "group": arguments.group,
        "curated_api_dir": display_path(curated_api_dir),
        "requested_adversary_names": arguments.adversary_name,
        "poll_timeout_reached": poll_timeout_reached,
        "quiescent_plateau_reached": quiescent_plateau_reached,
        "effective_quiescent_seconds": effective_quiescent_seconds,
        "counts": {
            "curated_abilities": sum(1 for artifact in artifacts if artifact.kind == "ability"),
            "curated_adversaries": sum(1 for artifact in artifacts if artifact.kind == "adversary"),
            "red_agents": len(agents),
            "operations": len(operations),
        },
        "agents": agents,
        "artifacts": [
            {"kind": artifact.kind, "path": display_path(artifact.path), "name": artifact.name}
            for artifact in artifacts
        ],
        "empty_caldera": None
        if empty_result is None
        else empty_result,
        "load_log": load_log,
        "operation_creation": operation_creation,
        "operations": summarize_operations(operations),
    }

    json_path, md_path = write_results(
        payload,
        update_latest=not arguments.adversary_name,
    )
    print(f"Wrote JSON summary to {json_path}")
    print(f"Wrote Markdown summary to {md_path}")
    if arguments.adversary_name:
        print("Skipped latest summary update because this was a subset rerun.")


if __name__ == "__main__":
    main()
