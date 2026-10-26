"""Projekt-Freigabe auf dem Mac (docs/plans/mac-file-sharing.md §2.2–2.3): Kern schreibt Anfrage-Dateien, der
root-Daemon (installer/lib/mac-shares-ctl.sh) setzt sie um und meldet den Zustand. Linux bleibt unverändert.
"""
from __future__ import annotations

import pytest

from hydrahive.samba import _mac, manager
from hydrahive.system import addons_status as st

PID = "0123456789abcdef01234567"


@pytest.fixture
def mac(monkeypatch, tmp_path):
    shares = tmp_path / "mac-shares.d"
    shares.mkdir()
    monkeypatch.setattr(manager, "is_mac", lambda: True)
    monkeypatch.setattr(_mac, "shares_dir", lambda: shares)
    monkeypatch.setattr(_mac, "account_exists", lambda: True)
    monkeypatch.setattr(_mac, "smbd_running", lambda: True)
    return shares


def test_freigeben_schreibt_anfrage_mit_festem_pfad(mac) -> None:
    from hydrahive.projects._paths import workspace_path

    ok, err = manager.enable_share(PID, "Mein Projekt!")
    assert ok and err == ""
    want = (mac / f"{PID}.want").read_text().splitlines()
    assert want == ["on", "Mein_Projekt", str(workspace_path(PID))]


def test_zustand_kommt_vom_daemon(mac) -> None:
    manager.enable_share(PID, "P")
    assert manager.is_share_enabled(PID) is False, "erst wenn der Daemon „on“ meldet"
    (mac / f"{PID}.state").write_text("on\n")
    assert manager.is_share_enabled(PID) is True
    (mac / f"{PID}.state").write_text("error:sharing\n")
    assert manager.is_share_enabled(PID) is False


def test_abschalten_schreibt_off(mac) -> None:
    (mac / f"{PID}.state").write_text("on\n")
    ok, _ = manager.disable_share(PID)
    assert ok and (mac / f"{PID}.want").read_text().splitlines()[0] == "off"


def test_ohne_installation_kein_freigeben(mac, monkeypatch) -> None:
    monkeypatch.setattr(_mac, "account_exists", lambda: False)
    assert manager.enable_share(PID, "P") == (False, "samba_not_installed")
    assert not (mac / f"{PID}.want").exists()


@pytest.mark.parametrize("bad", ["../etc", "a/b", "", "x" * 80, "a b", "id;rm"])
def test_projekt_id_wird_geprueft(mac, bad) -> None:
    assert manager.enable_share(bad, "P") == (False, "samba_bad_project")
    assert list(mac.iterdir()) == []


def test_status_auf_dem_mac(mac, monkeypatch) -> None:
    s = manager.samba_status()
    assert s["installed"] is True and s["running"] is True and s["platform"] == "mac"
    assert s["user"] == "hhshare"
    monkeypatch.setattr(_mac, "account_exists", lambda: False)
    assert manager.samba_status()["installed"] is False


def test_linux_unveraendert(monkeypatch, tmp_path) -> None:
    """Linux: weiter smb.conf-Schnipsel im includes-Ordner, kein Anfrage-Ordner."""
    monkeypatch.setattr(manager, "is_mac", lambda: False)
    inc = tmp_path / "hh-projects.d"
    inc.mkdir()
    from hydrahive.settings import settings
    monkeypatch.setattr(type(settings), "samba_includes_dir", property(lambda self: inc), raising=False)
    monkeypatch.setattr(manager, "_reload_smbd", lambda: True)
    assert manager.enable_share(PID, "P") == (True, "")
    assert (inc / f"{PID}.conf").exists() and "[P]" in (inc / f"{PID}.conf").read_text()
    assert manager.is_share_enabled(PID) is True
    assert "platform" not in manager.samba_status() or manager.samba_status()["platform"] == "linux"


def test_freigabe_konto_heisst_auf_dem_mac_hhshare(mac) -> None:
    assert manager.share_user() == "hhshare"


def test_mac_zusatzmodul_samba_installierbar(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(st, "is_mac", lambda: True)
    monkeypatch.setattr(st, "is_wsl", lambda: False)
    monkeypatch.setattr(st, "PROBES", {a: (lambda: False) for a in st.ADDONS})
    items = {i["id"]: i for i in st.list_addons(tmp_path / "install.conf")}
    assert items["samba"]["hint"] is None
    assert items["vms"]["hint"] == "mac" and items["whatsapp"]["hint"] == "mac"


@pytest.fixture
def projekt(client, admin_headers):
    r = client.post("/api/projects", headers=admin_headers,
                    json={"name": "Freigabe Test", "llm_model": "test/model", "members": []})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    yield pid
    client.delete(f"/api/projects/{pid}", headers=admin_headers)


def test_route_meldet_plattform_und_konto_auf_dem_mac(client, admin_headers, projekt, mac) -> None:
    r = client.get(f"/api/projects/{projekt}/samba", headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["platform"] == "mac" and d["user"] == "hhshare" and d["enabled"] is False
    r = client.put(f"/api/projects/{projekt}/samba", headers=admin_headers, json={"enabled": True})
    assert r.status_code == 200 and (mac / f"{projekt}.want").read_text().startswith("on\n")
    (mac / f"{projekt}.state").write_text("on\n")
    assert client.get(f"/api/projects/{projekt}/samba", headers=admin_headers).json()["enabled"] is True


def test_route_linux_plattform(client, admin_headers, projekt, monkeypatch) -> None:
    monkeypatch.setattr(manager, "is_mac", lambda: False)
    d = client.get(f"/api/projects/{projekt}/samba", headers=admin_headers).json()
    assert d["platform"] == "linux" and d["user"] == manager.settings.samba_user


def test_route_mac_nicht_installiert(client, admin_headers, projekt, mac, monkeypatch) -> None:
    monkeypatch.setattr(_mac, "account_exists", lambda: False)
    r = client.put(f"/api/projects/{projekt}/samba", headers=admin_headers, json={"enabled": True})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "samba_not_installed"
