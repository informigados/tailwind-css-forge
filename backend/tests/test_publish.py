from __future__ import annotations

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
        self.last_test_config: dict | None = None
        self.last_publish_config: dict | None = None

    def test_connection(self, config: dict) -> dict:
        self.last_test_config = config
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


def _wait_for_terminal_build(client, build_id: str, timeout_seconds: float = 5.0) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        payload = client.get(f"/api/builds/{build_id}").json()
        if payload["status"] in {"success", "failed", "cancelled"}:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Build {build_id} did not finish within {timeout_seconds} seconds.")


def _create_successful_build(client, tmp_path: Path) -> tuple[str, str]:
    _stub_process_runner(client)
    source_path = tmp_path / "publish-site"
    source_path.mkdir()
    (source_path / "index.html").write_text(
        """
        <html>
          <head>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
            <style type="text/tailwindcss">@theme { --color-brand: #2563eb; }</style>
          </head>
          <body class="bg-slate-950 text-white">Publish</body>
        </html>
        """,
        encoding="utf-8",
    )

    project_id = client.post("/api/projects/import", json={"source_path": str(source_path)}).json()["project"]["id"]
    client.post(f"/api/projects/{project_id}/analyze")
    build_id = client.post(f"/api/projects/{project_id}/build", json={"minify": True}).json()["build"]["id"]
    _wait_for_terminal_build(client, build_id)
    return project_id, build_id


def test_create_and_list_publish_profiles_masks_password(client, tmp_path: Path) -> None:
    project_id, _ = _create_successful_build(client, tmp_path)

    response = client.post(
        f"/api/projects/{project_id}/publish/profiles",
        json={
            "name": "Servidor FTP",
            "protocol": "ftp",
            "host": "ftp.example.com",
            "port": 21,
            "username": "forge",
            "password": "secret-123",
            "remote_path": "/public_html",
            "passive_mode": True,
        },
    )

    assert response.status_code == 201
    profile = response.json()["profile"]
    assert profile["has_password"] is True
    assert "password" not in profile
    assert profile["ftp_security_mode"] == "explicit_tls"
    assert profile["sftp_host_key_policy"] == "trust_on_first_use"

    list_response = client.get(f"/api/projects/{project_id}/publish/profiles")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["name"] == "Servidor FTP"


def test_publish_connection_uses_inline_profile(client, tmp_path: Path) -> None:
    project_id, _ = _create_successful_build(client, tmp_path)
    fake_ftp = FakePublisher("ftp")
    client.app.state.publish_service.publishers["ftp"] = fake_ftp

    response = client.post(
        f"/api/projects/{project_id}/publish/test",
        json={
            "profile": {
                "name": "Teste FTP",
                "protocol": "ftp",
                "host": "ftp.example.com",
                "port": 21,
                "username": "forge",
                "password": "secret-123",
                "remote_path": "/site",
                "passive_mode": True,
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_ftp.last_test_config["password"] == "secret-123"
    assert fake_ftp.last_test_config["ftp_security_mode"] == "explicit_tls"


def test_publish_build_ftp_uses_saved_profile_with_decrypted_password(client, tmp_path: Path) -> None:
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
            "passive_mode": False,
        },
    )
    profile_id = profile_response.json()["profile"]["id"]

    publish_response = client.post(
        f"/api/builds/{build_id}/publish/ftp",
        json={"profile_id": profile_id},
    )

    assert publish_response.status_code == 201
    payload = publish_response.json()
    assert payload["success"] is True
    assert payload["protocol"] == "ftp"
    assert fake_ftp.last_publish_config["password"] == "secret-123"
    assert fake_ftp.last_publish_config["passive_mode"] is False
    assert fake_ftp.last_publish_config["ftp_security_mode"] == "explicit_tls"


def test_publish_build_sftp_supports_inline_credentials(client, tmp_path: Path) -> None:
    project_id, build_id = _create_successful_build(client, tmp_path)
    fake_sftp = FakePublisher("sftp")
    client.app.state.publish_service.publishers["sftp"] = fake_sftp

    publish_response = client.post(
        f"/api/builds/{build_id}/publish/sftp",
        json={
            "profile": {
                "name": "Prod SFTP",
                "protocol": "sftp",
                "host": "sftp.example.com",
                "port": 22,
                "username": "forge",
                "password": "secret-456",
                "remote_path": "/var/www/site",
                "passive_mode": True,
            }
        },
    )

    assert publish_response.status_code == 201
    payload = publish_response.json()
    assert payload["success"] is True
    assert payload["protocol"] == "sftp"
    assert fake_sftp.last_publish_config["password"] == "secret-456"
    assert fake_sftp.last_publish_config["sftp_host_key_policy"] == "trust_on_first_use"
    assert fake_sftp.last_publish_config["known_hosts_path"]


def test_update_and_delete_publish_profile(client, tmp_path: Path) -> None:
    project_id, _ = _create_successful_build(client, tmp_path)

    created = client.post(
        f"/api/projects/{project_id}/publish/profiles",
        json={
            "name": "Stage FTP",
            "protocol": "ftp",
            "host": "ftp.stage.example.com",
            "port": 21,
            "username": "forge",
            "password": "secret-123",
            "remote_path": "/stage",
            "passive_mode": True,
        },
    )
    profile_id = created.json()["profile"]["id"]

    updated = client.put(
        f"/api/projects/{project_id}/publish/profiles/{profile_id}",
        json={
            "name": "Prod FTP",
            "protocol": "ftp",
            "host": "ftp.prod.example.com",
            "port": 21,
            "username": "forge-prod",
            "password": "",
            "remote_path": "/prod",
            "passive_mode": False,
        },
    )

    assert updated.status_code == 200
    profile = updated.json()["profile"]
    assert profile["name"] == "Prod FTP"
    assert profile["host"] == "ftp.prod.example.com"
    assert profile["has_password"] is True
    assert profile["passive_mode"] is False
    assert profile["ftp_security_mode"] == "explicit_tls"

    deleted = client.delete(f"/api/projects/{project_id}/publish/profiles/{profile_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_profile_id"] == profile_id

    remaining = client.get(f"/api/projects/{project_id}/publish/profiles")
    assert remaining.status_code == 200
    assert remaining.json() == []
