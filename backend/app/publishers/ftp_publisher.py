from __future__ import annotations

from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path, PurePosixPath


class FtpPublisher:
    protocol = "ftp"

    def test_connection(self, config: dict) -> dict:
        ftp = self._connect(config)
        ftp.quit()
        return {
            "protocol": self.protocol,
            "host": config["host"],
            "port": config["port"],
            "success": True,
            "message": "Conexão FTP validada com sucesso.",
        }

    def publish_directory(self, local_dir: Path, config: dict) -> dict:
        ftp = self._connect(config)
        remote_root = config["remote_path"].strip() or "/"
        files_uploaded = 0

        self._ensure_remote_dir(ftp, remote_root)
        for file_path in sorted(local_dir.rglob("*")):
            if file_path.is_dir():
                continue
            relative_parent = file_path.relative_to(local_dir).parent.as_posix()
            remote_dir = remote_root if relative_parent == "." else f"{remote_root.rstrip('/')}/{relative_parent}"
            self._ensure_remote_dir(ftp, remote_dir)
            remote_file = str(PurePosixPath(remote_dir) / file_path.name)
            with file_path.open("rb") as handle:
                ftp.storbinary(f"STOR {remote_file}", handle)
            files_uploaded += 1

        ftp.quit()
        return {
            "protocol": self.protocol,
            "remote_path": remote_root,
            "files_uploaded": files_uploaded,
            "success": True,
            "message": "Publicação FTP concluída com sucesso.",
        }

    def _connect(self, config: dict) -> FTP:
        security_mode = config.get("ftp_security_mode", "explicit_tls")
        if security_mode == "explicit_tls":
            ftp = FTP_TLS()
            ftp.connect(config["host"], config["port"], timeout=15)
            ftp.auth()
            ftp.login(config["username"], config["password"])
            ftp.prot_p()
        elif security_mode == "insecure_plaintext":
            ftp = FTP()
            ftp.connect(config["host"], config["port"], timeout=15)
            ftp.login(config["username"], config["password"])
        else:
            raise RuntimeError("Modo de segurança FTP inválido.")
        ftp.set_pasv(config.get("passive_mode", True))
        return ftp

    def _ensure_remote_dir(self, ftp: FTP, remote_path: str) -> None:
        normalized = remote_path.strip().strip("/") or ""
        if normalized == ".":
            normalized = ""
        if not normalized:
            return

        current = ""
        for segment in normalized.split("/"):
            current = f"{current}/{segment}" if current else f"/{segment}"
            try:
                ftp.mkd(current)
            except error_perm as exc:
                if not str(exc).startswith("550"):
                    raise
