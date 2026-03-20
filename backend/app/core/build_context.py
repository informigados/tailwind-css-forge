from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class BuildContext:
    project_id: str
    build_id: str
    workspace_path: Path
    src_path: Path
    dist_path: Path
    temp_path: Path
    reports_path: Path
    backups_path: Path
    analysis: dict
    build_plan: dict
    strategy: str
    env: dict[str, str] = field(default_factory=dict)
    progress_callback: Callable[[int, str, str], None] | None = None
    cancel_check: Callable[[], None] | None = None
