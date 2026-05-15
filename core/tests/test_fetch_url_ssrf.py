"""SSRF-Schutz in fetch_url — Unit-Tests für _is_blocked()."""
from __future__ import annotations

import pytest

from hydrahive.tools.fetch_url import _is_blocked


# --- Hostname-Denylist -------------------------------------------------------

def test_localhost_geblockt():
    assert _is_blocked("localhost") is True


def test_localhost_grossschreibung_geblockt():
    assert _is_blocked("LOCALHOST") is True


def test_metadata_google_geblockt():
    assert _is_blocked("metadata.google.internal") is True


def test_metadata_internal_geblockt():
    assert _is_blocked("metadata.internal") is True


# --- IP-Literal direkt geblockt ----------------------------------------------

def test_loopback_ipv4_geblockt():
    assert _is_blocked("127.0.0.1") is True


def test_loopback_andere_127er_geblockt():
    assert _is_blocked("127.0.0.2") is True


def test_private_10er_geblockt():
    assert _is_blocked("10.0.0.1") is True


def test_private_192_168_geblockt():
    assert _is_blocked("192.168.1.1") is True


def test_private_172_16_geblockt():
    assert _is_blocked("172.16.0.1") is True


def test_link_local_169_geblockt():
    assert _is_blocked("169.254.169.254") is True


def test_ipv6_loopback_geblockt():
    assert _is_blocked("::1") is True


# --- öffentliche Adressen erlaubt --------------------------------------------

def test_oeffentliche_ip_erlaubt():
    assert _is_blocked("1.1.1.1") is False


def test_oeffentliche_ip_google_erlaubt():
    assert _is_blocked("8.8.8.8") is False


def test_leerer_hostname_geblockt():
    assert _is_blocked("") is True
