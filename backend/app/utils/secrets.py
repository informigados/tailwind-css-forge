from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet


class SecretManager:
    def __init__(self, secrets_root: Path) -> None:
        self.secrets_root = secrets_root
        self.key_path = secrets_root / "fernet.key"

    def encrypt(self, value: str) -> str:
        token = self._fernet().encrypt(value.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, token: str) -> str:
        value = self._fernet().decrypt(token.encode("utf-8"))
        return value.decode("utf-8")

    def _fernet(self) -> Fernet:
        self.secrets_root.mkdir(parents=True, exist_ok=True)
        if not self.key_path.exists():
            self.key_path.write_bytes(Fernet.generate_key())
            self._restrict_key_permissions()
        else:
            self._restrict_key_permissions()
        return Fernet(self.key_path.read_bytes())

    def _restrict_key_permissions(self) -> None:
        if os.name == "nt":
            return
        self.key_path.chmod(0o600)
