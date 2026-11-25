"""install.conf nur über eine feste Liste bekannter Schlüssel laden (Task 42a25db7, Security-Review #762).

install.conf ist vom Dienstnutzer beschreibbar, update.sh läuft als root. Früher wurde jeder Schlüssel exportiert – die Datei
konnte so HH_SUDOERS_FILE/HH_UNIT_FILE/HH_NGINX_SITE (wohin root beim Rückweg schreibt), HH_SYSTEM_PYTHON (was root
ausführt) oder BASH_ENV (wird von jedem späteren `bash …`-Aufruf als root gesourct) setzen.
Getestet mit echtem bash: die Bibliothek direkt und der ECHTE Kopf von update.sh gegen ein Attrappen-Repo.
Gegenprobe: mit der alten Schleife in update.sh wird test_update_kopf_* rot (HH_SUDOERS_FILE/BASH_ENV kommen durch).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.test_update_safety import UPDATE, _env, make_env

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "installer" / "lib" / "install-conf.sh"
INSTALL = REPO / "installer" / "install.sh"

# Was eine fremd beschriebene install.conf früher setzen konnte – darf nie durchkommen.
GEFAEHRLICH = {
    "HH_SUDOERS_FILE": "/tmp/boese-sudoers",
    "HH_UNIT_FILE": "/tmp/boese-unit",
    "HH_NGINX_SITE": "/tmp/boese-site",
    "HH_SYSTEM_PYTHON": "/tmp/boese-python",
    "HH_HOST": "0.0.0.0",
    "HH_PORT": "9999",
    "HH_BACKUP_ROOT": "/tmp/boese-backup",
    "HH_DB_TOOL": "/tmp/boese-tool",
    "BASH_ENV": "/tmp/boese-bashenv",
    "LD_PRELOAD": "/tmp/boese.so",
}


def _clean_env(**extra: str) -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if not k.startswith("HH_") and k not in GEFAEHRLICH}
    return {**base, "LANG": "C.UTF-8", **extra}


def _load(conf: Path, show: list[str], **env: str) -> subprocess.CompletedProcess[str]:
    prints = "; ".join(f'echo "{k}=${{{k}:-<leer>}}"' for k in show)
    script = f'set -euo pipefail; source "{LIB}"; hh_load_install_conf "{conf}"; {prints}'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=_clean_env(**env), timeout=30)


def _vals(out: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def test_bekannte_schluessel_werden_uebernommen(tmp_path: Path) -> None:
    """Fängt: Allowlist zu eng – die Komponenten-Auswahl ginge beim Update verloren (Module nicht mehr gepflegt)."""
    conf = tmp_path / "install.conf"
    conf.write_text("# Kommentar\nHH_INSTALL_VOICE='yes'\nHH_INSTALL_VMS=\"no\"\nHH_SYSTEM_UPGRADE=no\n"
                    "HH_TAILSCALE_AUTHKEY='tskey-auth-abc_123'\nHH_INSTALL_LOCAL_MEDIA=yes")   # letzte Zeile ohne \n
    r = _load(conf, ["HH_INSTALL_VOICE", "HH_INSTALL_VMS", "HH_SYSTEM_UPGRADE", "HH_TAILSCALE_AUTHKEY",
                     "HH_INSTALL_LOCAL_MEDIA"])
    assert r.returncode == 0, r.stderr
    assert _vals(r.stdout) == {"HH_INSTALL_VOICE": "yes", "HH_INSTALL_VMS": "no", "HH_SYSTEM_UPGRADE": "no",
                               "HH_TAILSCALE_AUTHKEY": "tskey-auth-abc_123", "HH_INSTALL_LOCAL_MEDIA": "yes"}
    assert r.stderr == ""


def test_env_gewinnt_ueber_datei(tmp_path: Path) -> None:
    """Fängt: Datei überschreibt die Umgebung (sudo -E HH_INSTALL_VOICE=no ./update.sh muss gelten)."""
    conf = tmp_path / "install.conf"
    conf.write_text("HH_INSTALL_VOICE=yes\n")
    r = _load(conf, ["HH_INSTALL_VOICE"], HH_INSTALL_VOICE="no")
    assert _vals(r.stdout)["HH_INSTALL_VOICE"] == "no"


def test_root_relevante_schluessel_werden_ignoriert(tmp_path: Path) -> None:
    """Fängt den eigentlichen Befund: Pfade/Programme/BASH_ENV aus der Datei bestimmen, was root schreibt oder ausführt."""
    conf = tmp_path / "install.conf"
    conf.write_text("".join(f"{k}='{v}'\n" for k, v in GEFAEHRLICH.items()) + "HH_INSTALL_VOICE=yes\n")
    r = _load(conf, [*GEFAEHRLICH, "HH_INSTALL_VOICE"])
    assert r.returncode == 0, r.stderr
    v = _vals(r.stdout)
    assert {k: v[k] for k in GEFAEHRLICH} == {k: "<leer>" for k in GEFAEHRLICH}
    assert v["HH_INSTALL_VOICE"] == "yes"
    # Im Log stehen die Namen, nie die Werte (die Datei ist fremd beschreibbar).
    for k, val in GEFAEHRLICH.items():
        assert k in r.stderr
        assert val not in r.stderr


@pytest.mark.parametrize("zeile", [
    "HH_INSTALL_VOICE='yes; touch /tmp/x'",
    "HH_INSTALL_VOICE=$(touch /tmp/x)",
    "HH_INSTALL_VOICE=ja",
    "HH_SYSTEM_UPGRADE=",
    "HH_TAILSCALE_AUTHKEY='abc --exit-node=1.2.3.4'",
])
def test_ungueltige_werte_werden_ignoriert(tmp_path: Path, zeile: str) -> None:
    """Fängt: bekannter Schlüssel mit untergeschobenem Wert (Leerzeichen/Optionen/Befehle) wird trotzdem exportiert."""
    conf = tmp_path / "install.conf"
    conf.write_text(zeile + "\n")
    key = zeile.split("=", 1)[0]
    r = _load(conf, [key])
    # Der untergeschobene Wert kommt nie durch; Zusatz-Module gelten dann als „no“, alles andere bleibt leer.
    assert _vals(r.stdout)[key] == ("no" if key == "HH_INSTALL_VOICE" else "<leer>")


@pytest.mark.parametrize("wert", ["ja", "true", "1", "YES"])
def test_ungueltiger_wert_bei_zusatzmodul_gilt_als_no(tmp_path: Path, wert: str) -> None:
    """Fängt (Review #778): ungültiger Wert → „kein Wert“ → hh_addon_wanted schreibt yes und update.sh installiert das Modul.

    Früher galt so ein Wert als „nicht yes“ (Modul nicht gepflegt); er darf die Auswahl nicht still umkehren.
    """
    conf = tmp_path / "install.conf"
    conf.write_text(f"HH_INSTALL_VOICE={wert}\nHH_INSTALL_POSTGRES={wert}\n")
    r = _load(conf, ["HH_INSTALL_VOICE", "HH_INSTALL_POSTGRES"])
    v = _vals(r.stdout)
    assert v["HH_INSTALL_VOICE"] == "no"
    assert v["HH_INSTALL_POSTGRES"] == "<leer>"      # Kern-Schalter: „!= no“ → wie früher weiter gepflegt
    assert wert not in r.stderr.replace("[install.conf]", "")


def test_ungueltiger_wert_ueberschreibt_die_umgebung_nicht(tmp_path: Path) -> None:
    conf = tmp_path / "install.conf"
    conf.write_text("HH_INSTALL_VOICE=ja\n")
    assert _vals(_load(conf, ["HH_INSTALL_VOICE"], HH_INSTALL_VOICE="yes").stdout)["HH_INSTALL_VOICE"] == "yes"


def test_crlf_datei_wird_gelesen(tmp_path: Path) -> None:
    """Fängt: Datei mit Windows-Zeilenenden – jeder Wert endet auf \\r, alles würde verworfen (Module dann still „yes“)."""
    conf = tmp_path / "install.conf"
    conf.write_bytes(b"HH_INSTALL_VOICE='no'\r\nHH_INSTALL_VMS=yes\r\nHH_SYSTEM_UPGRADE=no\r\n")
    r = _load(conf, ["HH_INSTALL_VOICE", "HH_INSTALL_VMS", "HH_SYSTEM_UPGRADE"])
    assert _vals(r.stdout) == {"HH_INSTALL_VOICE": "no", "HH_INSTALL_VMS": "yes", "HH_SYSTEM_UPGRADE": "no"}
    assert r.stderr == ""


def test_update_modus_laedt_tailscale_schluessel_nicht(tmp_path: Path) -> None:
    """Fängt (Security-Review #778): root meldet den Server beim Update mit einem vom Dienstnutzer gewählten Schlüssel an."""
    conf = tmp_path / "install.conf"
    conf.write_text("HH_TAILSCALE_AUTHKEY='tskey-fremd'\nHH_INSTALL_TAILSCALE=yes\n")
    show = 'echo "HH_TAILSCALE_AUTHKEY=${HH_TAILSCALE_AUTHKEY:-<leer>}"; echo "HH_INSTALL_TAILSCALE=$HH_INSTALL_TAILSCALE"'
    r = subprocess.run(["bash", "-c", f'set -euo pipefail; source "{LIB}"; hh_load_install_conf "{conf}" update; {show}'],
                       capture_output=True, text=True, env=_clean_env(), timeout=30)
    assert _vals(r.stdout) == {"HH_TAILSCALE_AUTHKEY": "<leer>", "HH_INSTALL_TAILSCALE": "yes"}
    # Aus der Umgebung geht es weiter (bewusster Aufruf durch den Admin).
    r = subprocess.run(["bash", "-c", f'set -euo pipefail; source "{LIB}"; hh_load_install_conf "{conf}" update; {show}'],
                       capture_output=True, text=True, env=_clean_env(HH_TAILSCALE_AUTHKEY="tskey-admin"), timeout=30)
    assert _vals(r.stdout)["HH_TAILSCALE_AUTHKEY"] == "tskey-admin"


def test_kaputter_schluesselname_bricht_nicht_ab_und_landet_nicht_im_log(tmp_path: Path) -> None:
    """Fängt: `export "$key=…"` mit Unsinn-Namen bricht update.sh (set -e) ab, oder Steuerzeichen landen im Log."""
    conf = tmp_path / "install.conf"
    conf.write_text("bad key\x1b[31m=1\nHH_INSTALL_VOICE=yes\n")
    r = _load(conf, ["HH_INSTALL_VOICE"])
    assert r.returncode == 0, r.stderr
    assert _vals(r.stdout)["HH_INSTALL_VOICE"] == "yes"
    assert "\x1b" not in r.stderr and "<ungültig>" in r.stderr


def test_fehlende_datei_ist_kein_fehler(tmp_path: Path) -> None:
    r = _load(tmp_path / "gibtsnicht.conf", ["HH_INSTALL_VOICE"])
    assert r.returncode == 0 and _vals(r.stdout)["HH_INSTALL_VOICE"] == "<leer>"


# --- der echte Kopf von update.sh ----------------------------------------------------------------------------------

def test_update_kopf_uebernimmt_keine_root_pfade_aus_install_conf(tmp_path: Path) -> None:
    """Task 42a25db7: install.conf setzt HH_SUDOERS_FILE=/tmp/x → der Rückweg darf nicht dorthin schreiben.

    Der Rückweg nimmt HH_SUDOERS_FILE/HH_UNIT_FILE/HH_NGINX_SITE aus der Umgebung (update-rollback.sh _rb_config). Geprüft
    wird der ECHTE Kopf von update.sh bis direkt nach dem Laden von install.conf (Sperre, Bibliotheken, Laden): danach
    darf keiner dieser Werte aus der Datei stammen.
    """
    e = make_env(tmp_path)
    (e["cfg"] / "install.conf").write_text("".join(f"{k}='{v}'\n" for k, v in GEFAEHRLICH.items())
                                           + "HH_INSTALL_VOICE='yes'\nHH_TAILSCALE_AUTHKEY='tskey-fremd'\n")
    show = "; ".join(f'echo "{k}=${{{k}:-<leer>}}"' for k in [*GEFAEHRLICH, "HH_INSTALL_VOICE", "HH_TAILSCALE_AUTHKEY"])
    t = UPDATE.read_text()
    nach_laden = t.index('\ncd "$HH_REPO_DIR"\n')          # erste Zeile nach dem Laden (alte und neue Fassung)
    script = t[:nach_laden] + f"\n{show}\necho KOPF-OK\nexit 0\n"
    env = {k: v for k, v in _env(e).items() if k not in GEFAEHRLICH}   # Testumgebung setzt Pfade sonst selbst (ENV gewinnt)
    r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=120, cwd=e["repo"])
    assert "KOPF-OK" in r.stdout, r.stdout + r.stderr
    v = _vals(r.stdout)
    assert {k: v[k] for k in GEFAEHRLICH} == {k: "<leer>" for k in GEFAEHRLICH}
    assert v["HH_INSTALL_VOICE"] == "yes"
    assert v["HH_TAILSCALE_AUTHKEY"] == "<leer>"          # nur für die Erstanmeldung (install.sh)


def test_update_und_install_laden_nur_ueber_die_allowlist() -> None:
    """Fängt: eine zweite, alte Lade-Schleife (export "$key=$value") bleibt in update.sh oder install.sh stehen."""
    for path in (UPDATE, INSTALL):
        code = "\n".join(l for l in path.read_text().splitlines() if not l.lstrip().startswith("#"))
        assert 'hh_load_install_conf "$INSTALL_CONF"' in code, path.name
        assert 'export "$key=$value"' not in code, path.name
    assert 'hh_load_install_conf "$INSTALL_CONF" update' in UPDATE.read_text()
