import sqlite3
from pathlib import Path

import pytest

from projectctl.central_store import CONTROL_DB_SCHEMA_VERSION, CentralControlStore


def test_control_store_bootstraps_versioned_schema(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")

    assert store.db_schema_version() == CONTROL_DB_SCHEMA_VERSION


def test_control_store_memory_database_persists_across_operations():
    store = CentralControlStore(":memory:")
    store.upsert_project({
        "project_id": "demo",
        "project_name": "Demo",
        "root_path": "/tmp/demo-project",
        "project_status": "active",
        "current_milestone": None,
        "human_gate": False,
        "scaffold_version": "0.1.0",
        "schema_version": "1",
        "package_compatibility": ">=0.1,<1.0",
        "compatibility_status": "compatible",
        "compatibility_reason": "ok",
    })

    assert store.get_project("demo")["project_name"] == "Demo"


def test_control_store_rejects_newer_database_schema(tmp_path: Path):
    path = tmp_path / "newer.db"
    connection = sqlite3.connect(path)
    connection.execute(f"PRAGMA user_version = {CONTROL_DB_SCHEMA_VERSION + 1}")
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="newer than supported"):
        CentralControlStore(path)


def test_run_id_cannot_move_between_projects(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    for project_id in ("one", "two"):
        store.upsert_project({
            "project_id": project_id,
            "project_name": project_id,
            "root_path": str(tmp_path / project_id),
            "project_status": "active",
            "current_milestone": None,
            "human_gate": False,
            "scaffold_version": "0.1.0",
            "schema_version": "1",
            "package_compatibility": ">=0.1,<1.0",
            "compatibility_status": "compatible",
            "compatibility_reason": "ok",
        })

    store.upsert_run("one", "run-1", "RUNNING")

    with pytest.raises(ValueError, match="already registered"):
        store.upsert_run("two", "run-1", "RUNNING")
