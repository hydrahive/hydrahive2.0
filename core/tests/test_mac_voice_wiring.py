"""Voice auf dem Mac: Zusatz-Modul im Cockpit, Runner, Update und Installer (Plan docs/plans/mac-voice.md)."""
from __future__ import annotations

import os
import subprocess

from hydrahive.system import addons_status as st
from tests.test_mac_containers_wiring import RUNNER, UPDATE, _exe, _run_install, runner  # noqa: F401  (Fixture)

ALL = ["containers", "vms", "samba", "whatsapp", "voice", "tailscale"]


# --- Kern: Zusatz-Modul -----------------------------------------------------------------------------------------

def _items(monkeypatch, tmp_path, *, mac: bool) -> dict:
    monkeypatch.setattr(st, "PROBES", {a: (lambda: False) for a in ALL})
    monkeypatch.setattr(st, "is_wsl", lambda: False)
    monkeypatch.setattr(st, "is_mac", lambda: mac)
    return {i["id"]: i for i in st.list_addons(tmp_path / "install.conf")}


def test_voice_installable_on_mac_without_containers(monkeypatch, tmp_path):
    items = _items(monkeypatch, tmp_path, mac=True)
    assert items["voice"]["hint"] is None
    assert items["voice"]["requires"] == []                       # Mac: läuft ohne Container
    assert all(items[a]["hint"] == "mac" for a in ("vms", "samba", "whatsapp"))


def test_voice_on_linux_still_needs_containers(monkeypatch, tmp_path):
    items = _items(monkeypatch, tmp_path, mac=False)
    assert items["voice"]["requires"] == ["containers"]
    assert items["voice"]["hint"] is None


def test_api_accepts_voice_install_on_mac(client, admin_headers, monkeypatch, tmp_path):
    from hydrahive.api.routes import system_addons as route

    monkeypatch.setattr(st, "PROBES", {a: (lambda: False) for a in ALL})
    monkeypatch.setattr(st, "is_wsl", lambda: False)
    monkeypatch.setattr(st, "is_mac", lambda: True)
    asked: list[str] = []
    monkeypatch.setattr(route, "request_install", lambda addon, *_: asked.append(addon))
    r = client.post("/api/system/addons/voice/install", headers=admin_headers)
    assert r.status_code == 202, r.text
    assert asked == ["voice"]


# --- Cockpit-Runner -------------------------------------------------------------------------------------------------

def _run_runner(r: dict) -> subprocess.CompletedProcess:
    env = {**os.environ, "HH_REPO_DIR": str(r["repo"]), "HH_DATA_DIR": str(r["data"]), "HH_USER": "tester",
           "HH_CONFIG_DIR": str(r["tmp"] / "etc")}
    return subprocess.run(["bash", str(RUNNER)], env=env, capture_output=True, text=True, timeout=60)


def test_runner_installs_voice_and_restarts_backend(runner):  # noqa: F811
    _exe(runner["repo"] / "installer" / "modules-mac" / "55-voice.sh",
         f'echo "55 user=$HH_USER" >> "{runner["log"]}"\n')
    runner["req"].write_text("install voice\n")
    res = _run_runner(runner)
    assert res.returncode == 0, res.stdout + res.stderr
    assert runner["log"].read_text().splitlines() == ["55 user=tester", "50"]
    assert "[hh2-addon] FERTIG: install voice ok" in res.stdout
    assert not runner["req"].exists()


# --- install-mac.sh / update-mac.sh ------------------------------------------------------------------------------

def test_install_voice_option(tmp_path):
    phases = _run_install(tmp_path, "--with=voice")
    assert "55-voice.sh" in phases
    assert phases.index("55-voice.sh") < phases.index("60-nginx.sh")
    assert "55-voice.sh" not in _run_install(tmp_path / "b")                  # Standard aus
    assert "55-voice.sh" in _run_install(tmp_path / "c", "--with=tailscale,voice")


def test_install_voice_env_option(tmp_path):
    assert "55-voice.sh" in _run_install(tmp_path, HH_INSTALL_VOICE="yes")


def _run_update_voice(tmp_path, conf_line: str) -> list[str]:
    """Nur den Voice-Block von update-mac.sh ausführen (zwischen „Voice“ und „Tailscale“)."""
    text = UPDATE.read_text()
    start = text.index("if grep -q '^HH_INSTALL_VOICE=yes'")
    end = text.index("if grep -q '^HH_INSTALL_TAILSCALE=yes'")
    repo, etc, ran = tmp_path / "repo", tmp_path / "etc", tmp_path / "ran.log"
    _exe(repo / "installer" / "modules-mac" / "55-voice.sh", f'echo "55 user=$HH_USER" >> "{ran}"\n')
    etc.mkdir(parents=True, exist_ok=True)
    (etc / "install.conf").write_text(conf_line + "\n")
    script = ('log() { echo "$*"; }\nto_log() { cat; }\n'
              f'HH_REPO_DIR="{repo}"\nHH_CONFIG_DIR="{etc}"\nHH_DATA_DIR="{tmp_path}"\nHH_USER=tester\n'
              + text[start:end])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    return ran.read_text().splitlines() if ran.exists() else []


def test_update_runs_voice_only_when_wanted(tmp_path):
    assert _run_update_voice(tmp_path / "a", "HH_INSTALL_VOICE=yes") == ["55 user=tester"]
    assert _run_update_voice(tmp_path / "b", "HH_INSTALL_VOICE=no") == []
    assert _run_update_voice(tmp_path / "c", "HH_INSTALL_TAILSCALE=yes") == []


def test_update_keeps_wanted_voice():
    text = UPDATE.read_text()
    i = text.index("modules-mac/55-voice.sh")
    block = text[i - 400:i + 300]
    assert "HH_INSTALL_VOICE=yes" in block                                     # nur wenn gewünscht
    assert "FEHLGESCHLAGEN" in block and "exit 1" not in block                  # bricht das Update nicht ab


def test_ui_text_no_longer_claims_container():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n" / "locales"
    for lang in ("de", "en"):
        import json
        desc = json.loads((root / lang / "system.json").read_text())
        found = [v for v in _walk(desc) if isinstance(v, str) and ("Spracherkennung" in v or "speech" in v.lower())]
        assert found, lang
        assert not any("Container" in v or "container" in v for v in found), found


def _walk(d):
    if isinstance(d, dict):
        for v in d.values():
            yield from _walk(v)
    else:
        yield d
