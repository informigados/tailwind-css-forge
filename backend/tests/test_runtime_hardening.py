from __future__ import annotations

from pathlib import Path

from app.db.init_db import init_db
from app.db.session import Database
from app.utils.secrets import SecretManager


def test_sqlite_uses_wal_and_busy_timeout(tmp_path: Path) -> None:
    database = Database(tmp_path / "forge.db")
    init_db(database)

    with database.connect() as connection:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]

    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) == 30000


def test_secret_manager_restricts_key_permissions_on_posix(tmp_path: Path, monkeypatch) -> None:
    manager = SecretManager(tmp_path / "secrets")
    chmod_calls: list[int] = []

    def recording_chmod(path: Path, mode: int) -> None:
        chmod_calls.append(mode)

    monkeypatch.setattr("app.utils.secrets.os.name", "posix")
    monkeypatch.setattr(Path, "chmod", recording_chmod)

    encrypted = manager.encrypt("forge-secret")

    assert encrypted
    assert chmod_calls == [0o600]
