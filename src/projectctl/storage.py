from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class YamlProjectStore:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.os_root = project_root / ".project-os"

    def load_yaml(self, relative_path: str) -> dict[str, Any]:
        path = self.os_root / relative_path
        if not path.exists():
            raise FileNotFoundError(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}

    def save_yaml(self, relative_path: str, data: dict[str, Any]) -> None:
        path = self.os_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
