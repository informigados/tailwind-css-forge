from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_rate_limit_blocks_repeated_mutating_requests(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime"
    source_path = tmp_path / "site"
    source_path.mkdir()
    (source_path / "index.html").write_text("<html><body>Forge</body></html>", encoding="utf-8")

    os.environ["FORGE_RUNTIME_PATH"] = str(runtime_path)
    os.environ["FORGE_DATABASE_PATH"] = str(runtime_path / "forge.db")
    os.environ["FORGE_API_RATE_LIMIT_WINDOW_SECONDS"] = "60"
    os.environ["FORGE_API_RATE_LIMIT_MAX_REQUESTS"] = "2"
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        response_one = client.post("/api/projects/import", json={"source_path": str(source_path)})
        response_two = client.post("/api/projects/import", json={"source_path": str(source_path)})
        response_three = client.post("/api/projects/import", json={"source_path": str(source_path)})

    os.environ.pop("FORGE_RUNTIME_PATH", None)
    os.environ.pop("FORGE_DATABASE_PATH", None)
    os.environ.pop("FORGE_API_RATE_LIMIT_WINDOW_SECONDS", None)
    os.environ.pop("FORGE_API_RATE_LIMIT_MAX_REQUESTS", None)
    get_settings.cache_clear()

    assert response_one.status_code == 201
    assert response_two.status_code == 201
    assert response_three.status_code == 429
    assert response_three.headers["Retry-After"] == "60"


def test_cors_preflight_uses_explicit_methods_and_headers(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime"

    os.environ["FORGE_RUNTIME_PATH"] = str(runtime_path)
    os.environ["FORGE_DATABASE_PATH"] = str(runtime_path / "forge.db")
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

    os.environ.pop("FORGE_RUNTIME_PATH", None)
    os.environ.pop("FORGE_DATABASE_PATH", None)
    get_settings.cache_clear()

    assert response.status_code == 200
    assert response.headers["access-control-allow-methods"] == "GET, POST, PUT, DELETE, OPTIONS"
    assert response.headers["access-control-allow-headers"] == "Accept, Accept-Language, Authorization, Content-Language, Content-Type, Origin"
