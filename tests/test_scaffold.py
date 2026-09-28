from pathlib import Path

import pytest
import yaml

from projectctl.scaffold import install_qa_scaffold, install_scaffold


def test_install_scaffold_copies_only_base_consumer_files(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")

    assert (tmp_path / "PROJECT.md").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".project-os/manifest.yaml").exists()
    assert (tmp_path / "specs/product").is_dir()
    assert (tmp_path / ".project-os/workflows").is_dir()
    assert (tmp_path / ".project-os/runs/runtime/checkpoints").is_dir()
    assert (tmp_path / ".project-os/runs/runtime/events").is_dir()
    assert (tmp_path / ".project-os/runs/runtime/approvals").is_dir()

    assert not (tmp_path / "scripts/qa.ps1").exists()
    assert not (tmp_path / "qa").exists()
    assert not (tmp_path / ".qa/runs").exists()

    assert not (tmp_path / "src").exists()
    assert not (tmp_path / "defaults").exists()
    assert not (tmp_path / "schemas").exists()
    assert not (tmp_path / "docs").exists()

    manifest = yaml.safe_load(
        (tmp_path / ".project-os/manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["project"]["id"] == "demo"
    assert manifest["project"]["name"] == "Demo"
    assert manifest["project_os"]["scaffold_version"] == "0.3.0"
    assert manifest["project_os"]["schema_version"] == "1"
    assert manifest["project_os"]["package_compatibility"] == ">=0.3,<1.0"


def test_install_scaffold_with_qa_adds_optional_overlay(tmp_path: Path):
    install_scaffold(
        tmp_path,
        project_id="demo",
        project_name="Demo",
        with_qa=True,
    )

    assert (tmp_path / "scripts/qa.ps1").exists()
    assert (tmp_path / "qa/README.md").exists()
    assert (tmp_path / "qa/result.example.json").exists()
    assert (tmp_path / "qa/scenarios/smoke.example.yaml").exists()
    assert (tmp_path / ".qa/.gitignore").exists()
    assert (tmp_path / ".qa/runs").is_dir()

    script = (tmp_path / "scripts/qa.ps1").read_text(encoding="utf-8")
    assert '__PROJECT_ID__' not in script
    assert '$projectName = "demo"' in script


def test_install_qa_scaffold_does_not_reinstall_base_scaffold(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    project_before = (tmp_path / "PROJECT.md").read_text(encoding="utf-8")

    install_qa_scaffold(
        tmp_path,
        project_id="demo",
        project_name="Demo",
    )

    assert (tmp_path / "PROJECT.md").read_text(encoding="utf-8") == project_before
    assert (tmp_path / "scripts/qa.ps1").exists()
    assert (tmp_path / ".qa/runs").is_dir()


def test_install_scaffold_protects_existing_project_file(tmp_path: Path):
    original = "# Existing project\n"
    (tmp_path / "PROJECT.md").write_text(original, encoding="utf-8")

    with pytest.raises(FileExistsError):
        install_scaffold(tmp_path, project_id="demo", project_name="Demo")

    assert (tmp_path / "PROJECT.md").read_text(encoding="utf-8") == original


def test_install_qa_scaffold_protects_existing_qa_file(tmp_path: Path):
    (tmp_path / "scripts").mkdir()
    existing = "# Existing QA implementation\n"
    (tmp_path / "scripts/qa.ps1").write_text(existing, encoding="utf-8")

    with pytest.raises(FileExistsError):
        install_qa_scaffold(
            tmp_path,
            project_id="demo",
            project_name="Demo",
        )

    assert (tmp_path / "scripts/qa.ps1").read_text(encoding="utf-8") == existing
