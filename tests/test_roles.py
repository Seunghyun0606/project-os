from pathlib import Path

import yaml

from projectctl.project import Project
from projectctl.roles import RolePolicyResolver
from projectctl.scaffold import install_scaffold


def test_role_permissions_use_defaults(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    resolver = RolePolicyResolver(Project(tmp_path))

    assert resolver.can_write("developer", "task_result") is True
    assert resolver.can_write("reviewer", "review_result") is True
    assert resolver.can_write("reviewer", "task_result") is False


def test_role_permissions_apply_project_override(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    profile_path = tmp_path / ".project-os/profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["overrides"] = {
        "roles": {
            "developer": {
                "writes": ["task_result", "decision_proposals"]
            }
        }
    }
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")

    resolver = RolePolicyResolver(Project(tmp_path))
    assert resolver.can_write("developer", "decision_proposals") is True
