"""install.sh core-first (docs/specs/installer-core-first.md §1, Till 11.10.: nginx + PostgreSQL im Kern).

Neue Installation: keine Fragen zu Zusatz-Modulen, alle aus; Kern (nginx, PostgreSQL, HydraLink) läuft immer.
Statische Prüfungen am Skript (Muster wie test_install_sh_local_media.py) + der Auswahl-Block wird echt ausgeführt.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

INSTALL = Path(__file__).resolve().parents[2] / "installer" / "install.sh"


def _text() -> str:
    return INSTALL.read_text()


def _choices_block() -> str:
    """Der Teil von install.sh zwischen den Markern – Auswahl laden, anwenden, speichern."""
    t = _text()
    return t[t.index("# >>> Auswahl"):t.index("# <<< Auswahl")]


def _run_choices(tmp: Path, args: str = "", env: dict[str, str] | None = None, conf: str | None = None):
    cfg = tmp / "etc"
    cfg.mkdir(exist_ok=True)
    if conf is not None:
        (cfg / "install.conf").write_text(conf)
    script = tmp / "choices.sh"
    script.write_text(
        "set -euo pipefail\n"
        'log() { :; }\nerr() { echo "$*" >&2; exit 1; }\n'
        f'INSTALLER_DIR="{INSTALL.parent}"\nHH_CONFIG_DIR="{cfg}"\n'
        'is_tty() { return 1; }\n'
        + _choices_block()
        + '\nfor v in HH_INSTALL_TAILSCALE HH_INSTALL_VOICE HH_INSTALL_CONTAINERS HH_INSTALL_VMS HH_INSTALL_SAMBA '
          'HH_INSTALL_WHATSAPP HH_INSTALL_LOCAL_MEDIA HH_INSTALL_POSTGRES HH_INSTALL_NGINX; do echo "$v=${!v:-}"; done\n')
    base = {k: v for k, v in os.environ.items() if not k.startswith("HH_INSTALL_")}
    r = subprocess.run(["bash", str(script), *args.split()], capture_output=True, text=True,
                       env={**base, "LANG": "C.UTF-8", **(env or {})})
    out = dict(line.split("=", 1) for line in r.stdout.splitlines() if line.startswith("HH_INSTALL_"))
    saved = (cfg / "install.conf").read_text() if (cfg / "install.conf").exists() else ""
    return r, out, saved


ADDONS = ("HH_INSTALL_TAILSCALE", "HH_INSTALL_VOICE", "HH_INSTALL_CONTAINERS", "HH_INSTALL_VMS",
          "HH_INSTALL_SAMBA", "HH_INSTALL_WHATSAPP", "HH_INSTALL_LOCAL_MEDIA")


def test_new_install_has_all_addons_off_and_saves_them(tmp_path):
    r, out, saved = _run_choices(tmp_path)
    assert r.returncode == 0, r.stderr
    assert {out[v] for v in ADDONS} == {"no"}
    for v in ADDONS:
        assert f"{v}='no'" in saved


def test_core_stays_on_without_asking(tmp_path):
    r, out, saved = _run_choices(tmp_path)
    assert out["HH_INSTALL_POSTGRES"] in ("", "yes") and out["HH_INSTALL_NGINX"] in ("", "yes")
    assert "HH_INSTALL_POSTGRES='no'" not in saved and "HH_INSTALL_NGINX='no'" not in saved


def test_existing_install_conf_is_respected(tmp_path):
    """Bestand: install.conf mit alter Auswahl bleibt unverändert gültig."""
    old = "HH_INSTALL_VOICE='yes'\nHH_INSTALL_VMS='yes'\nHH_INSTALL_SAMBA='no'\n"
    r, out, _ = _run_choices(tmp_path, conf=old)
    assert out["HH_INSTALL_VOICE"] == "yes" and out["HH_INSTALL_VMS"] == "yes" and out["HH_INSTALL_SAMBA"] == "no"


def test_all_and_with_flags(tmp_path):
    _, out, _ = _run_choices(tmp_path, "--all")
    assert {out[v] for v in ADDONS if v != "HH_INSTALL_LOCAL_MEDIA"} == {"yes"}
    _, out, _ = _run_choices(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path, "--with=samba")
    assert out["HH_INSTALL_SAMBA"] == "yes" and out["HH_INSTALL_VMS"] == "no"


def test_unknown_with_name_aborts(tmp_path):
    r, _, _ = _run_choices(tmp_path, "--with=postgres")
    assert r.returncode != 0


def test_env_still_wins(tmp_path):
    _, out, _ = _run_choices(tmp_path, env={"HH_INSTALL_VMS": "yes"})
    assert out["HH_INSTALL_VMS"] == "yes" and out["HH_INSTALL_VOICE"] == "no"


def test_no_component_questions_without_reconfigure():
    """Die Fragen (ask_yn) gibt es nur noch hinter --reconfigure; Kern-Teile werden nie gefragt."""
    t = _text()
    asks = re.findall(r"prompt_component (HH_INSTALL_[A-Z_]+)", t)
    assert "HH_INSTALL_POSTGRES" not in asks and "HH_INSTALL_NGINX" not in asks
    for m in re.finditer(r"\n\s*prompt_component HH_INSTALL_", t):
        before = t[:m.start()]
        assert before.rfind('if [ "$RECONFIGURE" = "1" ]') > before.rfind("\nfi"), "Frage außerhalb von --reconfigure"


def test_reconfigure_defaults_are_no():
    found = re.findall(r"prompt_component (HH_INSTALL_[A-Z_]+)\s+([yn])\s", _text())
    assert len(found) == 7, found                   # alle sieben Zusatz-Module, keins vergessen
    for var, default in found:
        assert default == "n", var


def test_preflight_runs_before_phase_1():
    t = _text()
    phase1 = t.index('log "Phase 1: System-Dependencies"')
    assert t.index("hh_apt_retries") < phase1 and t.index("hh_preflight_dns") < phase1
    assert "lib/preflight.sh" in t


def test_postgres_and_nginx_run_as_core():
    """PostgreSQL und nginx laufen ohne Auswahl (Notausstieg per ENV=no bleibt)."""
    t = _text()
    assert 'bash "$INSTALLER_DIR/modules/48-postgres.sh"' in t and 'bash "$INSTALLER_DIR/modules/60-nginx.sh"' in t


def test_summary_points_to_cockpit_for_addons():
    t = _text()
    assert "Admin-Cockpit → System → Zusatz-Module" in t
    assert "--reconfigure" in t
