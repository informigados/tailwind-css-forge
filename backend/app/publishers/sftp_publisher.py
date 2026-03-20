from __future__ import annotations

from pathlib import Path, PurePosixPath

from app.utils.fs import ensure_directory


class SftpPublisher:
    protocol = "sftp"

    def test_connection(self, config: dict) -> dict:
        client, sftp = self._connect(config)
        sftp.close()
        client.close()
        return {
            "protocol": self.protocol,
            "host": config["host"],
            "port": config["port"],
            "success": True,
            "message": "Conexão SFTP validada com sucesso.",
        }

    def publish_directory(self, local_dir: Path, config: dict) -> dict:
        client, sftp = self._connect(config)
        remote_root = config["remote_path"].strip() or "."
        files_uploaded = 0

        self._ensure_remote_dir(sftp, remote_root)
        for file_path in sorted(local_dir.rglob("*")):
            if file_path.is_dir():
                continue
            relative = file_path.relative_to(local_dir).as_posix()
            remote_file = f"{remote_root.rstrip('/')}/{relative}"
            remote_dir = str(PurePosixPath(remote_file).parent)
            self._ensure_remote_dir(sftp, remote_dir)
            sftp.put(str(file_path), remote_file)
            files_uploaded += 1

        sftp.close()
        client.close()
        return {
            "protocol": self.protocol,
            "remote_path": remote_root,
            "files_uploaded": files_uploaded,
            "success": True,
            "message": "Publicação SFTP concluída com sucesso.",
        }

    def _connect(self, config: dict):
        try:
            import paramiko
        except ImportError as exc:
            raise RuntimeError("Paramiko não está instalado; suporte SFTP indisponível.") from exc

        host_keys_path = Path(config["known_hosts_path"])
        ensure_directory(host_keys_path.parent)

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        if host_keys_path.exists():
            client.load_host_keys(str(host_keys_path))

        host_key_policy = config.get("sftp_host_key_policy", "trust_on_first_use")
        if host_key_policy == "strict":
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        elif host_key_policy == "trust_on_first_use":
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        else:
            raise RuntimeError("Politica de chave SFTP invalida.")

        client.connect(
            hostname=config["host"],
            port=config["port"],
            username=config["username"],
            password=config["password"],
            look_for_keys=False,
            allow_agent=False,
            timeout=15,
            auth_timeout=15,
            banner_timeout=15,
        )
        if host_key_policy == "trust_on_first_use":
            client.save_host_keys(str(host_keys_path))

        sftp = client.open_sftp()
        return client, sftp

    def _ensure_remote_dir(self, sftp, remote_path: str) -> None:
        normalized = remote_path.strip().strip("/") or ""
        if normalized == ".":
            normalized = ""
        if not normalized:
            return

        current = ""
        for segment in normalized.split("/"):
            current = f"{current}/{segment}" if current else f"/{segment}"
            try:
                sftp.mkdir(current)
            except OSError:
                pass
