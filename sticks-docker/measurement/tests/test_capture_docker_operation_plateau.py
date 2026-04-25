from __future__ import annotations

from types import SimpleNamespace

from sticks_docker.measurement.scripts import capture_docker_operation_plateau as module


def test_wait_for_plateau_returns_after_stable_fingerprint() -> None:
    operations = [
        {"id": "operation-1", "state": "running", "chain": [{"status": 0}, {"status": -3}]},
        {"id": "operation-2", "state": "running", "chain": [{"status": 0}, {"status": -3}]},
    ]
    snapshots = iter([operations, list(reversed(operations)), operations])

    runner = SimpleNamespace(
        api_get_json=lambda base_url, api_key, endpoint: next(snapshots),
        operations_fingerprint=lambda ops: tuple(
            (item["id"], item["state"], len(item["chain"]), tuple(link["status"] for link in item["chain"]))
            for item in sorted(ops, key=lambda item: item["id"])
        ),
        operations_are_quiescent=lambda ops, previous: previous is not None,
    )

    result = module.wait_for_plateau(
        runner,
        "http://127.0.0.1:8888",
        "ADMIN123",
        stable_polls=2,
        poll_interval_seconds=0,
        timeout_seconds=5,
    )

    assert result == operations
