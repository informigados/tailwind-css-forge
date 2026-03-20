from __future__ import annotations

import socket
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
        self._load_local_host_keys(client, host_keys_path)

        host_key_policy = config.get("sftp_host_key_policy", "trust_on_first_use")
        if host_key_policy not in {"strict", "trust_on_first_use"}:
            raise RuntimeError("Politica de chave SFTP invalida.")
        if host_key_policy == "trust_on_first_use":
            self._seed_trust_on_first_use_host_key(
                paramiko=paramiko,
                host_keys_path=host_keys_path,
                host=config["host"],
                port=config["port"],
            )
            self._load_local_host_keys(client, host_keys_path)

        client.set_missing_host_key_policy(paramiko.RejectPolicy())

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

        sftp = client.open_sftp()
        return client, sftp

    def _load_local_host_keys(self, client, host_keys_path: Path) -> None:
        if host_keys_path.exists():
            client.load_host_keys(str(host_keys_path))

    def _seed_trust_on_first_use_host_key(self, *, paramiko, host_keys_path: Path, host: str, port: int) -> None:
        host_key_name = self._known_hosts_host_name(host, port)
        host_keys = paramiko.HostKeys()
        if host_keys_path.exists():
            host_keys.load(str(host_keys_path))
            if host_key_name in host_keys:
                return

        sock = None
        transport = None
        try:
            sock = socket.create_connection((host, port), timeout=15)
            transport = paramiko.Transport(sock)
            transport.start_client(timeout=15)
            remote_host_key = transport.get_remote_server_key()
        except Exception as exc:  # pragma: no cover - exercised with paramiko/socket integration
            raise RuntimeError("Não foi possível validar a chave do host SFTP.") from exc
        finally:
            if transport is not None:
                transport.close()
            if sock is not None:
                sock.close()

        host_keys.add(host_key_name, remote_host_key.get_name(), remote_host_key)
        host_keys.save(str(host_keys_path))

    def _known_hosts_host_name(self, host: str, port: int) -> str:
        if port == 22:
            return host
        return f"[{host}]:{port}"

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
