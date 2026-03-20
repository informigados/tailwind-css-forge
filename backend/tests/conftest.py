from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    runtime_path = tmp_path / "runtime"
    database_path = runtime_path / "forge.db"
    os.environ["FORGE_RUNTIME_PATH"] = str(runtime_path)
    os.environ["FORGE_DATABASE_PATH"] = str(database_path)
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    os.environ.pop("FORGE_RUNTIME_PATH", None)
    os.environ.pop("FORGE_DATABASE_PATH", None)
    get_settings.cache_clear()
