"""macOS-Installer: Admin-Passwort im Abschluss-Kasten + psql-Pfad auf Apple Silicon.

Befund 10.10.2026: install-mac.sh suchte das Erstpasswort per `log show …`. In
dem Skript ist aber `log()` eine eigene Funktion – der Aufruf landete dort und
nie beim macOS-Befehl; außerdem schreibt launchd stderr in eine Datei, nicht ins
System-Log. Folge: der Kasten zeigte nie ein Passwort. Jetzt wie unter Linux aus
$HH_CONFIG_DIR/.admin_initial_password (lifespan.py schreibt sie).

48-postgres.sh setzte PATH fest auf /usr/local/opt/postgresql@16/bin (Intel).
Auf Apple Silicon liegt Homebrew unter /opt/homebrew → psql nicht gefunden,
Datenbank-User wurde still nicht angelegt (Fehler per `|| true` verschluckt).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
PW_HELPER = INSTALLER / "lib" / "mac-admin-password.sh"
INSTALL_MAC = INSTALLER / "install-mac.sh"
POSTGRES = INSTALLER / "modules-mac" / "48-postgres.sh"


def _run_helper(cfg: Path, tries: str = "1") -> subprocess.CompletedProcess:
    env = {**os.environ, "HH_CONFIG_DIR": str(cfg), "HH_PW_TRIES": tries}
    return subprocess.run(["bash", str(PW_HELPER)], env=env, capture_output=True,
                          text=True, timeout=30)


def test_passwort_wird_aus_datei_gelesen_und_geloescht(tmp_path: Path):
    pw_file = tmp_path / ".admin_initial_password"
    pw_file.write_text("Abc-123_xyz\n")
    r = _run_helper(tmp_path)
    assert r.returncode == 0
    assert r.stdout == "Abc-123_xyz"
    assert not pw_file.exists()


def test_ohne_datei_kein_passwort_und_kein_fehler(tmp_path: Path):
    r = _run_helper(tmp_path)
    assert r.returncode == 0
    assert r.stdout == ""


def test_leere_datei_zaehlt_nicht(tmp_path: Path):
    pw_file = tmp_path / ".admin_initial_password"
    pw_file.write_text("")
    r = _run_helper(tmp_path)
    assert r.stdout == ""


def test_wartet_bis_datei_erscheint(tmp_path: Path):
    pw_file = tmp_path / ".admin_initial_password"
    env = {**os.environ, "HH_CONFIG_DIR": str(tmp_path), "HH_PW_TRIES": "5"}
    proc = subprocess.Popen(["bash", str(PW_HELPER)], env=env, stdout=subprocess.PIPE, text=True)
    subprocess.run(["sleep", "1"], check=True)
    pw_file.write_text("spaet-da\n")
    out, _ = proc.communicate(timeout=20)
    assert out == "spaet-da"


def test_install_mac_nutzt_nicht_mehr_log_show():
    src = INSTALL_MAC.read_text()
    assert "log show" not in src
    assert "mac-admin-password.sh" in src


def test_postgres_pfad_nicht_fest_auf_intel():
    src = POSTGRES.read_text()
    assert "/usr/local/opt/postgresql@16/bin" not in src
    assert 'export PATH="$(brew --prefix postgresql@16)/bin:$PATH"' in src
