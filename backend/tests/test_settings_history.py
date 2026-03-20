from __future__ import annotations

import json
import time
from pathlib import Path


def _stub_process_runner(client) -> None:
    def fake_run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
        if command[:2] == ["npm", "install"]:
            (cwd / "node_modules").mkdir(parents=True, exist_ok=True)
            return "npm install stubbed"

        if command[:2] == ["npx", "@tailwindcss/cli"]:
            output_index = command.index("-o") + 1
            output_path = Path(command[output_index])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                ".bg-slate-950{background-color:#020617}.text-white{color:#fff}",
                encoding="utf-8",
            )
            return "tailwind build stubbed"

        raise AssertionError(f"Unexpected command: {command}")

    client.app.state.build_service.process_runner.run = fake_run


class FakePublisher:
    def __init__(self, protocol: str) -> None:
        self.protocol = protocol
        self.last_publish_config: dict | None = None

    def test_connection(self, config: dict) -> dict:
        return {
            "protocol": self.protocol,
            "host": config["host"],
            "port": config["port"],
            "success": True,
            "message": f"{self.protocol.upper()} connection ok",
        }

    def publish_directory(self, local_dir: Path, config: dict) -> dict:
        self.last_publish_config = config | {"local_dir": str(local_dir)}
        file_count = len([path for path in local_dir.rglob("*") if path.is_file()])
        return {
            "protocol": self.protocol,
            "remote_path": config["remote_path"],
            "files_uploaded": file_count,
            "success": True,
            "message": f"{self.protocol.upper()} publish ok",
        }


def _create_successful_build(client, tmp_path: Path) -> tuple[str, str]:
    _stub_process_runner(client)
    source_path = tmp_path / "history-site"
    source_path.mkdir()
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
            <style type="text/tailwindcss">@theme { --color-brand: #2563eb; }</style>
          </head>
          <body class="bg-slate-950 text-white">History</body>
        </html>
        """,
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")
    build_id = client.post(f"/api/projects/{project_id}/build", json={"minify": True}).json()["build"]["id"]
    deadline = time.time() + 5.0
    while time.time() < deadline:
        payload = client.get(f"/api/builds/{build_id}").json()
        if payload["status"] in {"success", "failed", "cancelled"}:
            return project_id, build_id
        time.sleep(0.05)
    raise AssertionError(f"Build {build_id} did not finish within 5 seconds.")


def test_settings_roundtrip(client) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    defaults = response.json()["settings"]
    assert defaults["language"] == "pt-BR"
    assert defaults["backup_before_build"] is True

    update = client.put(
        "/api/settings",
        json={
            "language": "en-US",
            "theme": "dark",
            "default_workspace_path": "C:/Forge/workspaces",
            "default_exports_path": "C:/Forge/exports",
            "backup_before_build": False,
            "default_minify": False,
            "detailed_logs": True,
            "build_timeout_seconds": 900,
        },
    )

    assert update.status_code == 200
    payload = update.json()["settings"]
    assert payload["language"] == "en-US"
    assert payload["theme"] == "dark"
    assert payload["backup_before_build"] is False
    assert payload["default_minify"] is False
    assert payload["build_timeout_seconds"] == 900


def test_settings_reject_unsupported_language_and_expose_i18n_metadata(client) -> None:
    metadata_response = client.get("/api/i18n")
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()
    assert metadata["default_locale"] == "pt-BR"
    assert "en-US" in metadata["supported_locales"]

    invalid_update = client.put(
        "/api/settings",
        json={
            "language": "es-ES",
            "theme": "dark",
            "default_workspace_path": "C:/Forge/workspaces",
            "default_exports_path": "C:/Forge/exports",
            "backup_before_build": False,
            "default_minify": False,
            "detailed_logs": True,
            "build_timeout_seconds": 900,
        },
    )

    assert invalid_update.status_code == 400
    assert "Idioma não suportado" in invalid_update.json()["detail"]


def test_history_endpoint_consolidates_builds_profiles_and_audit(client, tmp_path: Path) -> None:
    project_id, build_id = _create_successful_build(client, tmp_path)
    fake_ftp = FakePublisher("ftp")
    client.app.state.publish_service.publishers["ftp"] = fake_ftp

    profile_response = client.post(
        f"/api/projects/{project_id}/publish/profiles",
        json={
            "name": "Prod FTP",
            "protocol": "ftp",
            "host": "ftp.example.com",
            "port": 21,
            "username": "forge",
            "password": "secret-123",
            "remote_path": "/public_html",
            "passive_mode": True,
        },
    )
    profile_id = profile_response.json()["profile"]["id"]

    publish_response = client.post(
        f"/api/builds/{build_id}/publish/ftp",
        json={"profile_id": profile_id},
    )
    assert publish_response.status_code == 201

    history_response = client.get("/api/history")
    assert history_response.status_code == 200
    history_items = history_response.json()
    assert len(history_items) == 1
    item = history_items[0]
    assert item["project"]["id"] == project_id
    assert item["latest_build"]["id"] == build_id
    assert item["publish_profile_count"] == 1
    assert len(item["recent_audit_events"]) >= 2

    activity_response = client.get(f"/api/history/projects/{project_id}")
    assert activity_response.status_code == 200
    activity = activity_response.json()
    assert activity["project"]["id"] == project_id
    assert activity["recent_builds"][0]["id"] == build_id
    assert activity["publish_profile_count"] == 1
    event_types = {event["event_type"] for event in activity["recent_audit_events"]}
    assert "publish_profile_created" in event_types
    assert "build_published" in event_types


def test_project_activity_keeps_project_audit_events_even_with_many_unrelated_entries(client, tmp_path: Path) -> None:
    project_id, _ = _create_successful_build(client, tmp_path)
    database = client.app.state.database

    database.execute(
        """
        INSERT INTO audit_logs (id, event_type, payload_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            "audit_project_kept",
            "build_published",
            json.dumps({"project_id": project_id, "host": "kept.example.com"}),
            "2098-01-01T00:00:00.000000Z",
        ),
    )

    for index in range(250):
        database.execute(
            """
            INSERT INTO audit_logs (id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                f"audit_other_{index:03d}",
                "publish_connection_test",
                json.dumps({"project_id": "other-project", "host": f"other-{index}.example.com"}),
                f"2099-01-01T00:00:00.{index:06d}Z",
            ),
        )

    activity_response = client.get(f"/api/history/projects/{project_id}")

    assert activity_response.status_code == 200
    activity = activity_response.json()
    assert activity["project"]["id"] == project_id
    assert len(activity["recent_audit_events"]) == 1
    assert activity["recent_audit_events"][0]["event_type"] == "build_published"
