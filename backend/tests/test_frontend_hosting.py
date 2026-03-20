from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_serves_frontend_index_and_assets(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime"
    frontend_dist = tmp_path / "frontend-dist"
    assets_dir = frontend_dist / "assets"
    assets_dir.mkdir(parents=True)
    (frontend_dist / "index.html").write_text("<html><body>Forge UI</body></html>", encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('forge');", encoding="utf-8")

    os.environ["FORGE_RUNTIME_PATH"] = str(runtime_path)
    os.environ["FORGE_DATABASE_PATH"] = str(runtime_path / "forge.db")
    os.environ["FORGE_FRONTEND_DIST_PATH"] = str(frontend_dist)
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        root_response = client.get("/")
        asset_response = client.get("/assets/app.js")
        spa_response = client.get("/projects/import")

    os.environ.pop("FORGE_RUNTIME_PATH", None)
    os.environ.pop("FORGE_DATABASE_PATH", None)
    os.environ.pop("FORGE_FRONTEND_DIST_PATH", None)
    get_settings.cache_clear()

    assert root_response.status_code == 200
    assert "Forge UI" in root_response.text
    assert asset_response.status_code == 200
    assert "console.log" in asset_response.text
    assert spa_response.status_code == 200
    assert "Forge UI" in spa_response.text


def test_returns_setup_hint_when_frontend_is_missing(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime"
    frontend_dist = tmp_path / "missing-frontend"

    os.environ["FORGE_RUNTIME_PATH"] = str(runtime_path)
    os.environ["FORGE_DATABASE_PATH"] = str(runtime_path / "forge.db")
    os.environ["FORGE_FRONTEND_DIST_PATH"] = str(frontend_dist)
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/")

    os.environ.pop("FORGE_RUNTIME_PATH", None)
    os.environ.pop("FORGE_DATABASE_PATH", None)
    os.environ.pop("FORGE_FRONTEND_DIST_PATH", None)
    get_settings.cache_clear()

    assert response.status_code == 503
    assert "Frontend ainda não buildado" in response.text


def test_rejects_dangerous_frontend_asset_paths(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime"
    frontend_dist = tmp_path / "frontend-dist"
    assets_dir = frontend_dist / "assets"
    assets_dir.mkdir(parents=True)
    (frontend_dist / "index.html").write_text("<html><body>Forge UI</body></html>", encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('forge');", encoding="utf-8")

    os.environ["FORGE_RUNTIME_PATH"] = str(runtime_path)
    os.environ["FORGE_DATABASE_PATH"] = str(runtime_path / "forge.db")
    os.environ["FORGE_FRONTEND_DIST_PATH"] = str(frontend_dist)
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        traversal_response = client.get("/assets/%2e%2e/%2e%2e/README.md")
        null_byte_response = client.get("/assets/%00app.js")

    os.environ.pop("FORGE_RUNTIME_PATH", None)
    os.environ.pop("FORGE_DATABASE_PATH", None)
    os.environ.pop("FORGE_FRONTEND_DIST_PATH", None)
    get_settings.cache_clear()

    assert traversal_response.status_code == 404
    assert null_byte_response.status_code == 404
