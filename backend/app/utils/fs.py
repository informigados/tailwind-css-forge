from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterator


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict) -> None:
    ensure_directory(path.parent)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def iter_files(path: Path) -> Iterator[Path]:
    for item in path.rglob("*"):
        if item.is_file():
            yield item


def copy_project_tree(source: Path, destination: Path, ignored_names: tuple[str, ...]) -> None:
    if destination.exists():
        shutil.rmtree(destination)

    ignored = shutil.ignore_patterns(*ignored_names)
    shutil.copytree(source, destination, ignore=ignored)


def safe_resolve(path: Path) -> Path:
    return path.expanduser().resolve(strict=True)
