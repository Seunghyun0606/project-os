from pathlib import Path

from projectctl.runtime_stores import (
    FileApprovalGateway,
    FileCheckpointStore,
    FileEventStore,
)
from projectctl.scaffold import install_scaffold


def test_file_checkpoint_store_round_trip(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    store = FileCheckpointStore(tmp_path)

    store.save_checkpoint("run-1", {"status": "RUNNING", "next_step": 1})

    assert store.load_checkpoint("run-1") == {
        "status": "RUNNING",
        "next_step": 1,
    }


def test_file_event_store_preserves_append_order(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    store = FileEventStore(tmp_path)

    store.append_event({"run_id": "run-1", "type": "first"})
    store.append_event({"run_id": "run-1", "type": "second"})

    assert [event["type"] for event in store.read_events("run-1")] == [
        "first",
        "second",
    ]


def test_file_approval_gateway_is_idempotent_and_resolvable(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    gateway = FileApprovalGateway(tmp_path)

    first = gateway.request("release", {"run_id": "run-1", "step_id": "deploy"})
    second = gateway.request("release", {"run_id": "run-1", "step_id": "deploy"})

    assert first == second
    assert gateway.status(first) == "pending"

    gateway.resolve(first, "approved")
    assert gateway.status(first) == "approved"
