from __future__ import annotations

import hashlib
from pathlib import Path


def calculate_directory_fingerprint(path: Path, ignored_names: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    ignored = set(ignored_names)

    for item in sorted(path.rglob("*")):
        if any(part in ignored for part in item.parts):
            continue

        relative = item.relative_to(path).as_posix()
        if item.is_dir():
            digest.update(f"dir:{relative}".encode("utf-8"))
            continue

        stat = item.stat()
        digest.update(f"file:{relative}:{stat.st_size}:{int(stat.st_mtime)}".encode("utf-8"))

    return digest.hexdigest()
