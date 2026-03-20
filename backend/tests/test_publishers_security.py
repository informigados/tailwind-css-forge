from __future__ import annotations

import sys
from pathlib import Path

from app.publishers.ftp_publisher import FtpPublisher
from app.publishers.sftp_publisher import SftpPublisher


class FakeFtpBase:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def connect(self, host: str, port: int, timeout: int) -> None:
        self.calls.append(("connect", host, port, timeout))

    def login(self, username: str, password: str) -> None:
        self.calls.append(("login", username, password))

    def set_pasv(self, enabled: bool) -> None:
        self.calls.append(("set_pasv", enabled))


class FakeFtp(FakeFtpBase):
    pass


class FakeFtpTls(FakeFtpBase):
    def auth(self) -> None:
        self.calls.append(("auth",))

    def prot_p(self) -> None:
        self.calls.append(("prot_p",))


class FakePolicy:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeSftp:
    def close(self) -> None:
        return None


class FakeSshClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def load_system_host_keys(self) -> None:
        self.calls.append(("load_system_host_keys",))

    def load_host_keys(self, path: str) -> None:
        self.calls.append(("load_host_keys", path))

    def set_missing_host_key_policy(self, policy) -> None:
        self.calls.append(("set_policy", policy.name))

    def connect(self, **kwargs) -> None:
        self.calls.append(("connect", kwargs))

    def save_host_keys(self, path: str) -> None:
        self.calls.append(("save_host_keys", path))

    def open_sftp(self) -> FakeSftp:
        self.calls.append(("open_sftp",))
        return FakeSftp()

    def close(self) -> None:
        self.calls.append(("close",))


class FakeParamikoModule:
    def __init__(self) -> None:
        self.clients: list[FakeSshClient] = []

    def SSHClient(self) -> FakeSshClient:
        client = FakeSshClient()
        self.clients.append(client)
        return client

    def RejectPolicy(self) -> FakePolicy:
        return FakePolicy("reject")

    def AutoAddPolicy(self) -> FakePolicy:
        return FakePolicy("autoadd")


def test_ftp_publisher_uses_explicit_ftps_by_default(monkeypatch) -> None:
    fake_tls_instances: list[FakeFtpTls] = []

    def fake_tls_factory():
        instance = FakeFtpTls()
        fake_tls_instances.append(instance)
        return instance

    monkeypatch.setattr("app.publishers.ftp_publisher.FTP_TLS", fake_tls_factory)
    monkeypatch.setattr("app.publishers.ftp_publisher.FTP", FakeFtp)

    publisher = FtpPublisher()
    publisher._connect(
        {
            "host": "ftp.example.com",
            "port": 21,
            "username": "forge",
            "password": "secret",
            "passive_mode": True,
            "ftp_security_mode": "explicit_tls",
        },
    )

    assert fake_tls_instances
    assert ("auth",) in fake_tls_instances[0].calls
    assert ("prot_p",) in fake_tls_instances[0].calls
    assert ("set_pasv", True) in fake_tls_instances[0].calls


def test_ftp_publisher_allows_explicit_plaintext_opt_in(monkeypatch) -> None:
    fake_ftp_instances: list[FakeFtp] = []

    def fake_ftp_factory():
        instance = FakeFtp()
        fake_ftp_instances.append(instance)
        return instance

    monkeypatch.setattr("app.publishers.ftp_publisher.FTP", fake_ftp_factory)
    monkeypatch.setattr("app.publishers.ftp_publisher.FTP_TLS", FakeFtpTls)

    publisher = FtpPublisher()
    publisher._connect(
        {
            "host": "ftp.example.com",
            "port": 21,
            "username": "forge",
            "password": "secret",
            "passive_mode": False,
            "ftp_security_mode": "insecure_plaintext",
        },
    )

    assert fake_ftp_instances
    assert ("login", "forge", "secret") in fake_ftp_instances[0].calls
    assert ("set_pasv", False) in fake_ftp_instances[0].calls


def test_sftp_publisher_supports_strict_known_hosts_policy(monkeypatch, tmp_path: Path) -> None:
    fake_paramiko = FakeParamikoModule()
    monkeypatch.setitem(sys.modules, "paramiko", fake_paramiko)
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("saved", encoding="utf-8")

    publisher = SftpPublisher()
    client, sftp = publisher._connect(
        {
            "host": "sftp.example.com",
            "port": 22,
            "username": "forge",
            "password": "secret",
            "known_hosts_path": str(known_hosts),
            "sftp_host_key_policy": "strict",
        },
    )

    calls = fake_paramiko.clients[0].calls
    assert ("load_host_keys", str(known_hosts)) in calls
    assert ("set_policy", "reject") in calls
    assert not any(call[0] == "save_host_keys" for call in calls)
    sftp.close()
    client.close()


def test_sftp_publisher_supports_trust_on_first_use(monkeypatch, tmp_path: Path) -> None:
    fake_paramiko = FakeParamikoModule()
    monkeypatch.setitem(sys.modules, "paramiko", fake_paramiko)
    known_hosts = tmp_path / "ssh" / "known_hosts"

    publisher = SftpPublisher()
    client, sftp = publisher._connect(
        {
            "host": "sftp.example.com",
            "port": 22,
            "username": "forge",
            "password": "secret",
            "known_hosts_path": str(known_hosts),
            "sftp_host_key_policy": "trust_on_first_use",
        },
    )

    calls = fake_paramiko.clients[0].calls
    assert ("set_policy", "autoadd") in calls
    assert ("save_host_keys", str(known_hosts)) in calls
    sftp.close()
    client.close()
