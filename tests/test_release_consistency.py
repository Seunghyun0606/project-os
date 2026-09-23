import re
from pathlib import Path

import yaml

from projectctl import __version__
from projectctl.versioning import check_compatibility


ROOT = Path(__file__).resolve().parents[1]


def test_release_version_sources_stay_aligned():
    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)

    assert match is not None
    assert version_file == "0.2.0"
    assert match.group(1) == version_file
    assert __version__ == version_file


def test_current_package_supports_current_scaffold():
    manifest = yaml.safe_load(
        (ROOT / "scaffold/default/.project-os/manifest.yaml").read_text(encoding="utf-8")
    )
    project_os = manifest["project_os"]

    assert project_os["scaffold_version"] == "0.2.0"
    assert project_os["schema_version"] == "1"
    assert check_compatibility(
        __version__,
        project_os["package_compatibility"],
    ).compatible is True
