from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_product_metadata(repo_root: Path) -> dict[str, str]:
    defaults = {
        "app_name": "Tailwind CSS Forge",
        "version": "0.1.0",
    }
    candidates = [
        repo_root / "forge-product.json",
        repo_root.parent / "forge-product.json",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return defaults
        return {
            "app_name": str(raw.get("app_name", defaults["app_name"])),
            "version": str(raw.get("version", defaults["version"])),
        }
    return defaults


def _parse_origins(value: str | None) -> tuple[str, ...]:
    if not value:
        return ("http://127.0.0.1:5173", "http://localhost:5173")

    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return tuple(origins) or ("http://127.0.0.1:5173", "http://localhost:5173")


def _parse_positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    app_version: str
    repo_root: Path
    runtime_path: Path
    workspaces_path: Path
    logs_path: Path
    temp_path: Path
    exports_path: Path
    secrets_path: Path
    known_hosts_path: Path
    frontend_dist_path: Path
    database_path: Path
    allowed_origins: tuple[str, ...]
    api_rate_limit_window_seconds: int
    api_rate_limit_max_requests: int
    ignored_copy_names: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    repo_root = _repo_root()
    product_metadata = _load_product_metadata(repo_root)
    runtime_path = Path(
        os.getenv("FORGE_RUNTIME_PATH", repo_root / "runtime"),
    )
    if not runtime_path.is_absolute():
        runtime_path = (repo_root / runtime_path).resolve()

    database_path = Path(
        os.getenv("FORGE_DATABASE_PATH", runtime_path / "forge.db"),
    )
    if not database_path.is_absolute():
        database_path = (repo_root / database_path).resolve()

    known_hosts_path = Path(
        os.getenv("FORGE_PUBLISH_KNOWN_HOSTS_PATH", runtime_path / "ssh" / "known_hosts"),
    )
    if not known_hosts_path.is_absolute():
        known_hosts_path = (repo_root / known_hosts_path).resolve()

    frontend_dist_path = Path(
        os.getenv("FORGE_FRONTEND_DIST_PATH", repo_root / "frontend" / "dist"),
    )
    if not frontend_dist_path.is_absolute():
        frontend_dist_path = (repo_root / frontend_dist_path).resolve()

    return Settings(
        app_name=product_metadata["app_name"],
        app_env=os.getenv("FORGE_APP_ENV", "development"),
        app_version=product_metadata["version"],
        repo_root=repo_root,
        runtime_path=runtime_path.resolve(),
        workspaces_path=(runtime_path / "workspaces").resolve(),
        logs_path=(runtime_path / "logs").resolve(),
        temp_path=(runtime_path / "temp").resolve(),
        exports_path=(runtime_path / "exports").resolve(),
        secrets_path=(runtime_path / "secrets").resolve(),
        known_hosts_path=known_hosts_path.resolve(),
        frontend_dist_path=frontend_dist_path.resolve(),
        database_path=database_path.resolve(),
        allowed_origins=_parse_origins(os.getenv("FORGE_ALLOWED_ORIGINS")),
        api_rate_limit_window_seconds=_parse_positive_int(
            os.getenv("FORGE_API_RATE_LIMIT_WINDOW_SECONDS"),
            60,
        ),
        api_rate_limit_max_requests=_parse_positive_int(
            os.getenv("FORGE_API_RATE_LIMIT_MAX_REQUESTS"),
            120,
        ),
        ignored_copy_names=(
            ".git",
            ".hg",
            ".svn",
            ".idea",
            ".vscode",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
            ".next",
            ".nuxt",
            ".cache",
            ".turbo",
        ),
    )
