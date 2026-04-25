from __future__ import annotations

from pathlib import Path

from sticks_docker.measurement.scripts import summarize_docker_findings as module


def test_extract_campaign_bootstrap_scripts_reads_entrypoint_patterns(tmp_path: Path) -> None:
    entrypoint = tmp_path / "entrypoint.sh"
    entrypoint.write_text(
        "\n".join(
            [
                "#!/bin/bash",
                "/apt41_dust_suta.sh",
                "echo ready",
                "/shadowray_suta.sh",
            ]
        ),
        encoding="utf-8",
    )

    assert module.extract_campaign_bootstrap_scripts(entrypoint) == [
        "apt41_dust_suta.sh",
        "shadowray_suta.sh",
    ]


def test_parse_docker_networks_keeps_only_top_level_network_names(tmp_path: Path) -> None:
    compose_path = tmp_path / "docker-compose.yml"
    compose_path.write_text(
        "\n".join(
            [
                "services:",
                "  app:",
                "    image: demo",
                "networks:",
                "  local-network:",
                "    driver: bridge",
                "  caldera-kali-network:",
                "    ipam:",
                "      config:",
                "        - subnet: 172.20.0.0/24",
            ]
        ),
        encoding="utf-8",
    )

    assert module.parse_docker_networks(compose_path) == [
        "local-network",
        "caldera-kali-network",
    ]


def test_summarize_operations_reports_progress_and_blockers() -> None:
    execution_payload = {
        "operations": [
            {
                "name": "OP001",
                "state": "running",
                "step_count": 0,
                "chain_count": 6,
                "chain_status_counts": {"0": 4, "1": 1, "-3": 1},
                "adversary": {"name": "APT41 DUST"},
                "last_link": {
                    "technique_id": "T1505.003",
                    "name": "T1505.003 - Web Shell",
                    "command": "curl http://172.21.0.20/shell.php?cmd=id",
                    "status": -3,
                },
                "nonzero_links": [
                    {
                        "index": 5,
                        "status": 1,
                        "technique_id": "T1105",
                        "name": "T1105 - Ingress Tool Transfer",
                        "command": "scp ...",
                        "output": "False",
                    },
                    {
                        "index": 6,
                        "status": -3,
                        "technique_id": "T1505.003",
                        "name": "T1505.003 - Web Shell",
                        "command": "curl http://172.21.0.20/shell.php?cmd=id",
                        "output": "False",
                    },
                ],
            },
            {
                "name": "OP002",
                "state": "running",
                "step_count": 0,
                "chain_count": 5,
                "chain_status_counts": {"0": 4, "-3": 1},
                "adversary": {"name": "ShadowRay"},
                "last_link": {
                    "technique_id": "T1105",
                    "name": "T1105 - Ingress Tool Transfer",
                    "command": "sshpass ...",
                    "status": -3,
                },
                "nonzero_links": [
                    {
                        "index": 5,
                        "status": -3,
                        "technique_id": "T1105",
                        "name": "T1105 - Ingress Tool Transfer",
                        "command": "sshpass ...",
                        "output": "False",
                    }
                ],
            },
        ]
    }

    summary = module.summarize_operations(execution_payload)

    assert summary["operations_total"] == 2
    assert summary["operations_with_progress"] == 2
    assert summary["operations_with_zero_steps_and_nonzero_chain"] == 2
    assert summary["total_successful_links"] == 8
    assert summary["total_failed_links"] == 1
    assert summary["total_pending_links"] == 2
    assert summary["per_operation"][0]["blocking_technique_id"] == "T1505.003"
    assert summary["per_operation"][1]["blocking_technique_id"] == "T1105"
    assert summary["per_operation"][0]["failed_links"] == 1
    assert summary["per_operation"][0]["pending_links"] == 1
    assert summary["per_operation"][1]["pending_links"] == 1
    assert len(summary["per_operation"][0]["nonzero_links"]) == 2
    assert summary["per_operation"][0]["nonzero_links"][0]["technique_id"] == "T1105"


def test_render_markdown_mentions_nonzero_link_details() -> None:
    markdown = module.render_markdown(
        {
            "generated_at_utc": "2026-03-20T00:00:00+00:00",
            "architecture": {
                "shared_substrate_model": True,
                "networks": ["local-network"],
                "nginx_bootstrap_scripts": ["a.sh"],
                "db_bootstrap_scripts": ["b.sh"],
            },
            "runtime_reproducibility": {
                "repaired_script_count": 1,
                "generated_conf_files": ["agents.yml"],
                "architecture_patches": [".docker/caldera/Dockerfile"],
            },
            "execution": {
                "operations_with_progress": 1,
                "operations_total": 1,
                "total_successful_links": 4,
                "total_failed_links": 1,
                "total_pending_links": 0,
                "poll_timeout_reached": False,
                "quiescent_plateau_reached": True,
                "per_operation": [
                    {
                        "name": "OP001",
                        "adversary_name": "APT41 DUST",
                        "state": "running",
                        "chain_count": 5,
                        "successful_links": 4,
                        "failed_links": 1,
                        "pending_links": 0,
                        "blocking_technique_id": "T1105",
                        "blocking_technique_name": "T1105 - Ingress Tool Transfer",
                        "nonzero_links": [
                            {
                                "index": 5,
                                "status": 1,
                                "technique_id": "T1105",
                                "name": "T1105 - Ingress Tool Transfer",
                                "command": "scp ...",
                                "output": "False",
                            }
                        ],
                    }
                ],
            },
            "reproducibility_takeaways": ["One takeaway."],
        }
    )

    assert "Non-zero link 5" in markdown
    assert "scp ..." in markdown
