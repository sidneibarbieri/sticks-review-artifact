from __future__ import annotations

import json
from pathlib import Path

from sticks_docker.measurement.scripts import prepare_docker_runtime_context as module


def write_api_bundle(path: Path, items: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")


def test_prepare_runtime_context_repairs_shell_permissions(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    shell_script = source_root / ".docker" / "caldera" / "plugins" / "emu" / "download_payloads.sh"
    shell_script.parent.mkdir(parents=True)
    shell_script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    shell_script.chmod(0o644)

    prepared = module.prepare_runtime_context(source_root, tmp_path / "runtime")
    repaired_script = prepared.output_dir / ".docker" / "caldera" / "plugins" / "emu" / "download_payloads.sh"

    assert repaired_script.exists()
    assert repaired_script.stat().st_mode & 0o100
    assert not shell_script.stat().st_mode & 0o100
    assert Path(".docker/caldera/plugins/emu/download_payloads.sh") in prepared.repaired_scripts


def test_prepare_runtime_context_resets_transient_directories(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dbdata_file = source_root / ".docker" / "db" / "dbdata" / "seed.txt"
    kali_file = source_root / "kali-data" / "history.txt"
    dbdata_file.parent.mkdir(parents=True)
    kali_file.parent.mkdir(parents=True)
    dbdata_file.write_text("dirty\n", encoding="utf-8")
    kali_file.write_text("dirty\n", encoding="utf-8")

    prepared = module.prepare_runtime_context(source_root, tmp_path / "runtime")
    runtime_dbdata = prepared.output_dir / ".docker" / "db" / "dbdata"
    runtime_kali = prepared.output_dir / "kali-data"

    assert runtime_dbdata.exists()
    assert runtime_kali.exists()
    assert list(runtime_dbdata.iterdir()) == []
    assert list(runtime_kali.iterdir()) == []
    assert Path(".docker/db/dbdata") in prepared.reset_directories
    assert Path("kali-data") in prepared.reset_directories


def test_prepare_runtime_context_generates_missing_caldera_runtime_configs(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    (source_root / ".docker" / "caldera" / "conf").mkdir(parents=True)

    prepared = module.prepare_runtime_context(source_root, tmp_path / "runtime")
    agents_config = prepared.output_dir / ".docker" / "caldera" / "conf" / "agents.yml"
    payloads_config = prepared.output_dir / ".docker" / "caldera" / "conf" / "payloads.yml"

    assert agents_config.exists()
    assert payloads_config.exists()
    assert "implant_name: sandcat.go" in agents_config.read_text(encoding="utf-8")
    assert "standard_payloads: {}" in payloads_config.read_text(encoding="utf-8")
    assert Path(".docker/caldera/conf/agents.yml") in prepared.generated_conf_files
    assert Path(".docker/caldera/conf/payloads.yml") in prepared.generated_conf_files


def test_prepare_runtime_context_patches_arm64_specific_runtime_files(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    caldera_dockerfile = source_root / ".docker" / "caldera" / "Dockerfile"
    kali_dockerfile = source_root / ".docker" / "kali" / "Dockerfile"
    caldera_dockerfile.parent.mkdir(parents=True)
    kali_dockerfile.parent.mkdir(parents=True)
    caldera_dockerfile.write_text(
        "RUN curl -k -L https://go.dev/dl/go1.25.0.linux-amd64.tar.gz -o go1.25.0.linux-amd64.tar.gz\n",
        encoding="utf-8",
    )
    kali_dockerfile.write_text(
        "CMD [\"sh\", \"-c\", \"curl -s -X POST -H 'file:sandcat.go' -H 'platform:linux' http://caldera:8888/file/download\"]\n",
        encoding="utf-8",
    )

    prepared = module.prepare_runtime_context(
        source_root,
        tmp_path / "runtime",
        host_architecture="arm64",
    )

    patched_caldera = prepared.output_dir / ".docker" / "caldera" / "Dockerfile"
    patched_kali = prepared.output_dir / ".docker" / "kali" / "Dockerfile"

    assert "go1.25.0.linux-arm64.tar.gz" in patched_caldera.read_text(encoding="utf-8")
    assert "-H 'architecture:arm64'" in patched_kali.read_text(encoding="utf-8")
    assert Path(".docker/caldera/Dockerfile") in prepared.architecture_patches
    assert Path(".docker/kali/Dockerfile") in prepared.architecture_patches


def test_prepare_runtime_context_builds_curated_api_overlay(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    (source_root / ".docker" / "caldera" / "conf").mkdir(parents=True)
    api_root = module.SOURCE_CURATED_API_ROOT
    original_api_root = module.SOURCE_CURATED_API_ROOT
    module.SOURCE_CURATED_API_ROOT = tmp_path / "api-source"
    try:
        write_api_bundle(
            module.SOURCE_CURATED_API_ROOT / "apt41_dust_dag-ability.json",
            [
                {
                    "ability_id": "apt41-ingress",
                    "technique_id": "T1105",
                    "executors": [{"name": "sh", "platform": "linux", "command": "echo old"}],
                },
                {
                    "ability_id": "apt41-exfil",
                    "technique_id": "T1567.002",
                    "executors": [{"name": "sh", "platform": "linux", "command": "echo old"}],
                },
                {
                    "ability_id": "apt41-archive",
                    "technique_id": "T1560.001",
                    "executors": [{"name": "sh", "platform": "linux", "command": "echo old"}],
                }
            ],
        )
        write_api_bundle(
            module.SOURCE_CURATED_API_ROOT / "operation_midnighteclipse_dag-ability.json",
            [
                {
                    "ability_id": "midnight-final",
                    "technique_id": "T1053.003",
                    "executors": [{"name": "sh", "platform": "linux", "command": "echo old"}],
                }
            ],
        )
        write_api_bundle(
            module.SOURCE_CURATED_API_ROOT / "salesforce_data_exfiltration_dag-ability.json",
            [
                {
                    "ability_id": "salesforce-final",
                    "technique_id": "T1587.001",
                    "executors": [{"name": "sh", "platform": "linux", "command": "echo old"}],
                }
            ],
        )
        write_api_bundle(
            module.SOURCE_CURATED_API_ROOT / "outer_space_dag-adversary.json",
            [
            ],
        )
        (module.SOURCE_CURATED_API_ROOT / "outer_space_dag-adversary.json").write_text(
            json.dumps(
                {
                    "id": "outer-space",
                    "atomic_ordering": [
                        "6afb1856-6e5a-5f9f-8f8c-rothos",
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        write_api_bundle(
            module.SOURCE_CURATED_API_ROOT / "shadowray_dag-ability.json",
            [
                {
                    "ability_id": "5c0eccee-eee4-5d88-b6e5-c83b25d44eaa",
                    "technique_id": "T1588.002",
                    "executors": [{"name": "sh", "platform": "linux", "command": "echo old"}],
                }
            ],
        )
        (module.SOURCE_CURATED_API_ROOT / "shadowray_dag-adversary.json").write_text(
            json.dumps(
                {
                    "id": "shadowray",
                    "atomic_ordering": [
                        "5c0eccee-eee4-5d88-b6e5-c83b25d44eaa",
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        prepared = module.prepare_runtime_context(
            source_root,
            tmp_path / "runtime",
            api_overlay_dir=tmp_path / "api-overlay",
        )
    finally:
        module.SOURCE_CURATED_API_ROOT = original_api_root

    apt41_bundle = json.loads(
        (prepared.prepared_api_root / "apt41_dust_dag-ability.json").read_text(encoding="utf-8")
    )
    outer_space = json.loads(
        (prepared.prepared_api_root / "outer_space_dag-adversary.json").read_text(
            encoding="utf-8"
        )
    )
    shadowray_bundle = json.loads(
        (prepared.prepared_api_root / "shadowray_dag-ability.json").read_text(encoding="utf-8")
    )
    shadowray_adversary = json.loads(
        (prepared.prepared_api_root / "shadowray_dag-adversary.json").read_text(
            encoding="utf-8"
        )
    )

    assert prepared.prepared_api_root == tmp_path / "api-overlay"
    assert apt41_bundle[0]["executors"][0]["command"] == module.APT41_INGRESS_COMMAND
    assert apt41_bundle[1]["executors"][0]["command"] == module.APT41_EXFIL_COMMAND
    assert apt41_bundle[2]["executors"][0]["command"] == module.APT41_ARCHIVE_COMMAND
    assert outer_space["atomic_ordering"] == ["a8de43be-fcde-5302-9cfd-rothos"]
    assert shadowray_bundle[0]["ability_id"] == module.SHADOWRAY_TOOL_ABILITY_ID
    assert shadowray_adversary["atomic_ordering"] == [module.SHADOWRAY_TOOL_ABILITY_ID]
    assert Path("apt41_dust_dag-ability.json") in prepared.api_overlay_patches
    assert Path("outer_space_dag-adversary.json") in prepared.api_overlay_patches


def test_apt41_runtime_commands_include_resilience_guards() -> None:
    assert "for attempt in 1 2 3" in module.APT41_EXFIL_COMMAND
    assert "fetch/onedrive_archive" in module.APT41_EXFIL_COMMAND
    assert '{"key":"onedrive_archive","val":"apt41_dust_exfil.txt"}' in module.APT41_EXFIL_COMMAND
    assert "exit 1" in module.APT41_EXFIL_COMMAND
    assert "cp /etc/hosts /tmp/collected_data.txt" in module.APT41_ARCHIVE_COMMAND
    assert "tar -czf /tmp/collected_data.tar.gz -C /tmp collected_data.txt" in module.APT41_ARCHIVE_COMMAND
    assert "test -f /tmp/collected_data.tar.gz" in module.APT41_ARCHIVE_COMMAND


def test_render_markdown_summary_mentions_repaired_shells() -> None:
    markdown = module.render_markdown_summary(
        {
            "generated_at_utc": "2026-03-20T00:00:00+00:00",
            "host_architecture": "arm64",
            "source_docker_root": "/tmp/source",
            "prepared_runtime_root": "/tmp/runtime",
            "prepared_curated_api_root": "/tmp/api-overlay",
            "reset_directories": ["kali-data"],
            "repaired_scripts": [".docker/caldera/plugins/emu/download_payloads.sh"],
            "generated_conf_files": [".docker/caldera/conf/agents.yml"],
            "architecture_patches": [".docker/caldera/Dockerfile"],
            "api_overlay_patches": ["apt41_dust_dag-ability.json"],
        }
    )

    assert "# Docker Runtime Context Preparation" in markdown
    assert "`1`" in markdown
    assert "download_payloads.sh" in markdown
    assert "agents.yml" in markdown
    assert "arm64" in markdown
    assert ".docker/caldera/Dockerfile" in markdown
    assert "apt41_dust_dag-ability.json" in markdown
