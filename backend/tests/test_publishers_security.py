from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

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
        pass


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
        self.host_keys_instances: list[FakeHostKeys] = []

    def SSHClient(self) -> FakeSshClient:
        client = FakeSshClient()
        self.clients.append(client)
        return client

    def RejectPolicy(self) -> FakePolicy:
        return FakePolicy("reject")

    def HostKeys(self) -> "FakeHostKeys":
        host_keys = FakeHostKeys()
        self.host_keys_instances.append(host_keys)
        return host_keys

    def Transport(self, sock) -> "FakeTransport":
        return FakeTransport(sock)


class FakeHostKeys:
    def __init__(self) -> None:
        self.loaded_path: str | None = None
        self.saved_path: str | None = None
        self.entries: set[str] = set()
        self.add_calls: list[tuple[str, str, object]] = []

    def load(self, path: str) -> None:
        self.loaded_path = path

    def save(self, path: str) -> None:
        self.saved_path = path

    def add(self, host: str, key_type: str, key: object) -> None:
        self.entries.add(host)
        self.add_calls.append((host, key_type, key))

    def __contains__(self, item: str) -> bool:
        return item in self.entries


class FakeRemoteHostKey:
    def get_name(self) -> str:
        return "ssh-ed25519"


class FakeTransport:
    def __init__(self, sock) -> None:
        self.sock = sock
        self.started = False
        self.closed = False

    def start_client(self, timeout: int) -> None:
        self.started = True

    def get_remote_server_key(self) -> FakeRemoteHostKey:
        return FakeRemoteHostKey()

    def close(self) -> None:
        self.closed = True


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
    seed_calls: list[tuple[Path, str, int]] = []

    publisher = SftpPublisher()

    def seed_stub(*, paramiko, host_keys_path: Path, host: str, port: int) -> None:
        _ = paramiko
        seed_calls.append((host_keys_path, host, port))

    monkeypatch.setattr(
        publisher,
        "_seed_trust_on_first_use_host_key",
        seed_stub,
    )
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
    assert ("set_policy", "reject") in calls
    assert seed_calls == [(known_hosts, "sftp.example.com", 22)]
    assert not any(call[0] == "save_host_keys" for call in calls)
    sftp.close()
    client.close()


def test_sftp_tofu_seeds_known_hosts_before_connect(monkeypatch, tmp_path: Path) -> None:
    fake_paramiko = FakeParamikoModule()
    monkeypatch.setitem(sys.modules, "paramiko", fake_paramiko)
    fake_socket = SimpleNamespace(close=lambda: None)
    socket_calls: list[tuple[tuple[str, int], int]] = []

    def fake_create_connection(address: tuple[str, int], timeout: int):
        socket_calls.append((address, timeout))
        return fake_socket

    monkeypatch.setattr("app.publishers.sftp_publisher.socket.create_connection", fake_create_connection)

    publisher = SftpPublisher()
    known_hosts = tmp_path / "known_hosts"
    publisher._seed_trust_on_first_use_host_key(
        paramiko=fake_paramiko,
        host_keys_path=known_hosts,
        host="sftp.example.com",
        port=2222,
    )

    host_keys = fake_paramiko.host_keys_instances[0]
    assert socket_calls == [(("sftp.example.com", 2222), 15)]
    assert host_keys.saved_path == str(known_hosts)
    assert host_keys.add_calls
    assert host_keys.add_calls[0][0] == "[sftp.example.com]:2222"
