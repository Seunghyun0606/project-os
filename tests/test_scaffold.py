from pathlib import Path

import pytest
import yaml

from projectctl.scaffold import install_scaffold


def test_install_scaffold_copies_only_consumer_files(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")

    assert (tmp_path / "PROJECT.md").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".project-os/manifest.yaml").exists()
    assert (tmp_path / "specs/product").is_dir()

    assert not (tmp_path / "src").exists()
    assert not (tmp_path / "defaults").exists()
    assert not (tmp_path / "schemas").exists()
    assert not (tmp_path / "docs").exists()

    manifest = yaml.safe_load(
        (tmp_path / ".project-os/manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["project"]["id"] == "demo"
    assert manifest["project"]["name"] == "Demo"


def test_install_scaffold_protects_existing_project_file(tmp_path: Path):
    original = "# Existing project\n"
    (tmp_path / "PROJECT.md").write_text(original, encoding="utf-8")

    with pytest.raises(FileExistsError):
        install_scaffold(tmp_path, project_id="demo", project_name="Demo")

    assert (tmp_path / "PROJECT.md").read_text(encoding="utf-8") == original
