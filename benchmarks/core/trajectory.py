from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Trajectory:
    """Persist named, inspectable artifacts for one benchmark research run."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def write(self, name: str, value: Any) -> Path:
        if not name or Path(name).name != name or Path(name).suffix:
            raise ValueError("trajectory artifact names must be simple JSON basenames")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        return path
