"""Regression: Ollama unter der eigenen LAN-IP galt faelschlich als 'remote'.

Live gefunden auf tills Workstation: Ollama ist dort als
http://192.168.178.197:11434 konfiguriert — das ist die EIGENE LAN-IP des
Rechners. Die Pruefung akzeptierte nur localhost/127.0.0.1/::1, hielt den
eigenen Host also fuer einen fremden und blendete den llmfit-Hardware-Fit
komplett aus ("Fit unbekannt", VRAM/tok-s leer), obwohl llmfit dort exakt die
richtige Hardware gemessen haette.
"""
from __future__ import annotations

import socket

import pytest

from hydrahive.llm import _local_host


@pytest.fixture(autouse=True)
def _clear_cache():
    _local_host._cache_clear()
    yield
    _local_host._cache_clear()


@pytest.mark.parametrize("value", ["localhost", "127.0.0.1", "::1", "127.0.1.1"])
def test_loopback_is_local(value):
    assert _local_host.is_local_host(value) is True


@pytest.mark.parametrize("value", ["0.0.0.0", "::"])
def test_unspecified_is_local(value):
    assert _local_host.is_local_host(value) is True


def test_own_lan_ip_is_local(monkeypatch):
    """Der eigentliche Bug: eigene LAN-IP galt als fremder Rechner."""
    monkeypatch.setattr(_local_host, "_own_addresses", lambda: frozenset({"192.168.178.197"}))
    _local_host._cache_clear()
    assert _local_host.is_local_host("192.168.178.197") is True


def test_foreign_lan_ip_is_not_local(monkeypatch):
    """Ein echter Fremdrechner darf NICHT die Hardware dieses Hosts erben."""
    monkeypatch.setattr(_local_host, "_own_addresses", lambda: frozenset({"192.168.178.197"}))
    _local_host._cache_clear()
    assert _local_host.is_local_host("192.168.178.50") is False


def test_own_hostname_is_local(monkeypatch):
    monkeypatch.setattr(socket, "gethostname", lambda: "tills-master-wks")
    assert _local_host.is_local_host("tills-master-wks") is True
    assert _local_host.is_local_host("TILLS-MASTER-WKS") is True


def test_foreign_hostname_is_not_local(monkeypatch):
    monkeypatch.setattr(socket, "gethostname", lambda: "tills-master-wks")
    assert _local_host.is_local_host("some-other-box") is False


def test_ipv6_zone_suffix_is_stripped(monkeypatch):
    monkeypatch.setattr(_local_host, "_own_addresses", lambda: frozenset({"fe80::1"}))
    _local_host._cache_clear()
    assert _local_host.is_local_host("fe80::1%eth0") is True


def test_empty_hostname_is_not_local():
    assert _local_host.is_local_host("") is False
    assert _local_host.is_local_host(None) is False


def test_resolution_failure_falls_back_to_loopback_only(monkeypatch):
    """Kein DNS/Netz: lieber KEIN Fit als der Hardware-Fit des falschen Rechners."""
    def _boom(*_args, **_kwargs):
        raise OSError("no dns")

    monkeypatch.setattr(socket, "getaddrinfo", _boom)
    _local_host._cache_clear()
    assert _local_host.is_local_host("127.0.0.1") is True
    assert _local_host.is_local_host("192.168.178.197") is False
