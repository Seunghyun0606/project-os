from pathlib import Path

import yaml

from projectctl.doctor import inspect
from projectctl.project import Project
from projectctl.versioning import check_compatibility, parse_version


def test_parse_version_normalizes_short_versions():
    assert parse_version("1") == (1, 0, 0)
    assert parse_version("1.2") == (1, 2, 0)
    assert parse_version("1.2.3") == (1, 2, 3)


def test_compatibility_range():
    assert check_compatibility("0.1.0", ">=0.1,<1.0").compatible is True
    result = check_compatibility("1.0.0", ">=0.1,<1.0")
    assert result.compatible is False


def test_doctor_reports_incompatible_package(tmp_path: Path):
    (tmp_path / ".project-os/state").mkdir(parents=True)
    (tmp_path / ".project-os/quality").mkdir(parents=True)
    (tmp_path / ".project-os/context").mkdir(parents=True)
    (tmp_path / ".project-os/manifest.yaml").write_text(
        yaml.safe_dump({
            "project_os": {
                "scaffold_version": "0.1.0",
                "schema_version": "1",
                "package_compatibility": ">=9.0",
            },
            "project": {"id": "x", "name": "X"},
        }),
        encoding="utf-8",
    )
    (tmp_path / ".project-os/state/current.yaml").write_text("project_status: active\n", encoding="utf-8")
    (tmp_path / ".project-os/state/roadmap.yaml").write_text("milestones: []\n", encoding="utf-8")
    (tmp_path / ".project-os/state/backlog.yaml").write_text("tasks: []\n", encoding="utf-8")
    (tmp_path / ".project-os/profile.yaml").write_text("profile: default\n", encoding="utf-8")
    (tmp_path / ".project-os/quality/gates.yaml").write_text("required: {}\n", encoding="utf-8")
    (tmp_path / ".project-os/context/index.yaml").write_text("domains: {}\n", encoding="utf-8")
    (tmp_path / "PROJECT.md").write_text("# X\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")

    findings = inspect(Project(tmp_path))
    assert any("does not satisfy" in item.message for item in findings)
