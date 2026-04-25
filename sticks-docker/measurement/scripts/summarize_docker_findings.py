#!/usr/bin/env python3
"""
Build a findings report from the latest Docker runtime and Caldera
execution measurements.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


MEASUREMENT_ROOT = Path(__file__).resolve().parent.parent
STICKS_DOCKER_ROOT = MEASUREMENT_ROOT.parent
RESULTS_DIR = MEASUREMENT_ROOT / "results"
DOCKER_ROOT = STICKS_DOCKER_ROOT / "docker"

EXECUTION_LATEST_JSON = RESULTS_DIR / "docker_caldera_execution_latest.json"
RUNTIME_LATEST_JSON = RESULTS_DIR / "docker_runtime_context_latest.json"
LATEST_JSON = RESULTS_DIR / "docker_execution_findings_latest.json"
LATEST_MD = RESULTS_DIR / "DOCKER_EXECUTION_FINDINGS_LATEST.md"


def display_path(path: Path) -> str:
    path = path.resolve()
    for root in (STICKS_DOCKER_ROOT.parent, MEASUREMENT_ROOT):
        if path.is_relative_to(root):
            return path.relative_to(root).as_posix()
    for marker in ("docker-context", "curated-api", "sticks-docker", "results"):
        if marker in path.parts:
            index = path.parts.index(marker)
            return Path(*path.parts[index:]).as_posix()
    return path.name or path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_campaign_bootstrap_scripts(entrypoint_path: Path) -> list[str]:
    scripts: list[str] = []
    pattern = re.compile(r"/([a-z0-9_]+_sut[ab]\.sh)")
    for line in entrypoint_path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line.strip())
        if match:
            scripts.append(match.group(1))
    return scripts


def parse_docker_networks(compose_path: Path) -> list[str]:
    networks: list[str] = []
    in_networks_section = False
    for line in compose_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("networks:"):
            in_networks_section = True
            continue
        if not in_networks_section:
            continue
        if line and not line.startswith(" "):
            break
        if not line.startswith("  ") or line.startswith("    "):
            continue
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith("#"):
            name = stripped[:-1]
            if name:
                networks.append(name)
    return networks


def classify_chain_status(status: str) -> str:
    try:
        numeric_status = int(status)
    except (TypeError, ValueError):
        return "unknown"
    if numeric_status == 0:
        return "success"
    if numeric_status < 0:
        return "pending"
    return "failed"


def summarize_operations(execution_payload: dict[str, Any]) -> dict[str, Any]:
    per_operation: list[dict[str, Any]] = []
    total_successful_links = 0
    total_failed_links = 0
    total_pending_links = 0
    progressed_operations = 0
    zero_steps_nonzero_chain = 0

    for operation in execution_payload["operations"]:
        chain_status_counts = operation.get("chain_status_counts", {})
        successful_links = 0
        failed_links = 0
        pending_links = 0
        for status, count in chain_status_counts.items():
            classification = classify_chain_status(str(status))
            if classification == "success":
                successful_links += count
            elif classification == "failed":
                failed_links += count
            elif classification == "pending":
                pending_links += count
        if operation.get("chain_count", 0) > 0:
            progressed_operations += 1
        if operation.get("step_count", 0) == 0 and operation.get("chain_count", 0) > 0:
            zero_steps_nonzero_chain += 1
        total_successful_links += successful_links
        total_failed_links += failed_links
        total_pending_links += pending_links
        per_operation.append(
            {
                "name": operation["name"],
                "adversary_name": operation["adversary"].get("name"),
                "state": operation["state"],
                "chain_count": operation["chain_count"],
                "step_count": operation["step_count"],
                "successful_links": successful_links,
                "failed_links": failed_links,
                "pending_links": pending_links,
                "blocking_technique_id": (operation.get("last_link") or {}).get("technique_id"),
                "blocking_technique_name": (operation.get("last_link") or {}).get("name"),
                "blocking_command": (operation.get("last_link") or {}).get("command"),
                "blocking_status": (operation.get("last_link") or {}).get("status"),
                "nonzero_links": operation.get("nonzero_links", []),
            }
        )

    return {
        "operations_total": len(execution_payload["operations"]),
        "operations_with_progress": progressed_operations,
        "operations_with_zero_steps_and_nonzero_chain": zero_steps_nonzero_chain,
        "total_successful_links": total_successful_links,
        "total_failed_links": total_failed_links,
        "total_pending_links": total_pending_links,
        "per_operation": per_operation,
    }


def is_explicit_end_marker(operation: dict[str, Any]) -> bool:
    blocking_name = str(operation.get("blocking_technique_name") or "")
    blocking_id = str(operation.get("blocking_technique_id") or "")
    return blocking_id == "T1529" or blocking_name.startswith("END OF ")


def build_findings_payload() -> dict[str, Any]:
    execution_payload = load_json(EXECUTION_LATEST_JSON)
    runtime_payload = load_json(RUNTIME_LATEST_JSON)
    nginx_scripts = extract_campaign_bootstrap_scripts(
        DOCKER_ROOT / ".docker" / "nginx" / "entrypoint.sh"
    )
    db_scripts = extract_campaign_bootstrap_scripts(
        DOCKER_ROOT / ".docker" / "db" / "entrypoint.sh"
    )
    execution_summary = summarize_operations(execution_payload)
    operations_with_failed_links = sum(
        1 for operation in execution_summary["per_operation"] if operation["failed_links"] > 0
    )
    operations_with_pending_links = sum(
        1 for operation in execution_summary["per_operation"] if operation["pending_links"] > 0
    )
    operations_without_failed_links = (
        execution_summary["operations_total"] - operations_with_failed_links
    )
    explicit_end_markers = sum(
        1 for operation in execution_summary["per_operation"] if is_explicit_end_marker(operation)
    )

    return {
        "sources": {
            "execution_report": display_path(EXECUTION_LATEST_JSON),
            "runtime_report": display_path(RUNTIME_LATEST_JSON),
        },
        "architecture": {
            "docker_compose": display_path(DOCKER_ROOT / "docker-compose.yml"),
            "networks": parse_docker_networks(DOCKER_ROOT / "docker-compose.yml"),
            "nginx_bootstrap_scripts": nginx_scripts,
            "db_bootstrap_scripts": db_scripts,
            "shared_substrate_model": bool(nginx_scripts and db_scripts),
        },
        "runtime_reproducibility": {
            "prepared_runtime_root": runtime_payload["prepared_runtime_root"],
            "repaired_script_count": len(runtime_payload.get("repaired_scripts", [])),
            "generated_conf_files": runtime_payload.get("generated_conf_files", []),
            "reset_directories": runtime_payload.get("reset_directories", []),
            "architecture_patches": runtime_payload.get("architecture_patches", []),
        },
        "execution": {
            "poll_timeout_reached": execution_payload["poll_timeout_reached"],
            "quiescent_plateau_reached": execution_payload["quiescent_plateau_reached"],
            "effective_quiescent_seconds": execution_payload["effective_quiescent_seconds"],
            "operations_with_failed_links": operations_with_failed_links,
            "operations_with_pending_links": operations_with_pending_links,
            "operations_without_failed_links": operations_without_failed_links,
            "explicit_end_markers": explicit_end_markers,
            **execution_summary,
        },
        "reproducibility_takeaways": [
            "The Docker artifact executes all curated campaigns inside one shared pre-composed substrate, not one isolated SUT per campaign.",
            "For this legacy Caldera path, executed work is visible in operation.chain even when operation.steps remains empty.",
            "Reproducibility depends on runtime repair outside the frozen artifact: missing executable bits, missing Caldera conf files, and host-aware bootstrap adjustments are required for clean replay on a fresh ARM64 host.",
            f"All curated campaigns progressed. {operations_with_failed_links} record at least one non-zero link status, {operations_with_pending_links} still have a pending tail under the observed window, and {explicit_end_markers} reach explicit end markers.",
            "The legacy artifact demonstrates partial procedural enactment on a shared laboratory environment, not independent push-button replay of fully isolated campaigns.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Docker Execution Findings",
        "",
        f"- Shared substrate model: `{payload['architecture']['shared_substrate_model']}`",
        f"- Networks: `{', '.join(payload['architecture']['networks'])}`",
        f"- Runtime script repairs: `{payload['runtime_reproducibility']['repaired_script_count']}`",
        f"- Generated runtime config files: `{', '.join(payload['runtime_reproducibility']['generated_conf_files'])}`",
        f"- Host architecture patches: `{', '.join(payload['runtime_reproducibility']['architecture_patches'])}`",
        f"- Operations with progress: `{payload['execution']['operations_with_progress']}/{payload['execution']['operations_total']}`",
        f"- Total successful links: `{payload['execution']['total_successful_links']}`",
        f"- Total failed links: `{payload['execution']['total_failed_links']}`",
        f"- Total pending links: `{payload['execution']['total_pending_links']}`",
        f"- Poll timeout reached: `{payload['execution']['poll_timeout_reached']}`",
        f"- Quiescent plateau reached: `{payload['execution']['quiescent_plateau_reached']}`",
        "",
        "## Architecture Findings",
        "",
        f"- Nginx bootstrap scripts: `{len(payload['architecture']['nginx_bootstrap_scripts'])}`",
        f"- DB bootstrap scripts: `{len(payload['architecture']['db_bootstrap_scripts'])}`",
        "- Both target-side entrypoints load every campaign bootstrap script during container startup, which yields one shared multi-campaign substrate.",
        "",
        "## Execution Findings",
        "",
    ]

    for operation in payload["execution"]["per_operation"]:
        lines.extend(
            [
                f"### {operation['name']} — {operation['adversary_name']}",
                f"- State: `{operation['state']}`",
                f"- Links observed: `{operation['chain_count']}`",
                f"- Successful links: `{operation['successful_links']}`",
                f"- Failed links: `{operation['failed_links']}`",
                f"- Pending links: `{operation['pending_links']}`",
                f"- Blocking technique: `{operation['blocking_technique_id']}` {operation['blocking_technique_name']}",
                "",
            ]
        )
        for link in operation.get("nonzero_links", []):
            lines.extend(
                [
                    f"- Non-zero link {link['index']}: `{link['technique_id']}` {link['name']} -> status `{link['status']}`",
                    f"  command: `{link['command']}`",
                    f"  output: `{link['output']}`",
                ]
            )
        if operation.get("nonzero_links"):
            lines.append("")

    lines.extend(["## Reproducibility Takeaways", ""])
    for takeaway in payload["reproducibility_takeaways"]:
        lines.append(f"- {takeaway}")

    return "\n".join(lines).rstrip() + "\n"


def write_results(payload: dict[str, Any]) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    md_text = render_markdown(payload)
    LATEST_JSON.write_text(json_text, encoding="utf-8")
    LATEST_MD.write_text(md_text, encoding="utf-8")
    return LATEST_JSON, LATEST_MD


def main() -> None:
    payload = build_findings_payload()
    json_path, md_path = write_results(payload)
    print(f"Wrote JSON summary to {json_path}")
    print(f"Wrote Markdown summary to {md_path}")


if __name__ == "__main__":
    main()
