from pathlib import Path

from projectctl.project import find_project_root


def test_find_project_root_from_nested_directory(tmp_path: Path):
    (tmp_path / ".project-os").mkdir()
    (tmp_path / ".project-os/manifest.yaml").write_text("project_os: {}\n", encoding="utf-8")
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)

    assert find_project_root(nested) == tmp_path
