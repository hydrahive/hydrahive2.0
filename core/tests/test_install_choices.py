"""Installer core-first: Auswahl der Zusatz-Module (docs/specs/installer-core-first.md §1, §2).

installer/lib/install-choices.sh wird von install.sh (neue Installation: Zusatz-Module aus) und update.sh (nur gewünschte
Module pflegen, Bestand migrieren) gesourct. Getestet mit echtem bash gegen ein tmp-Verzeichnis.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "installer" / "lib" / "install-choices.sh"
ADDON_VARS = ("HH_INSTALL_TAILSCALE", "HH_INSTALL_VOICE", "HH_INSTALL_CONTAINERS", "HH_INSTALL_VMS",
              "HH_INSTALL_SAMBA", "HH_INSTALL_WHATSAPP", "HH_INSTALL_LOCAL_MEDIA")


def _run(cmd: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    base = {k: v for k, v in os.environ.items() if not k.startswith("HH_INSTALL_")}
    return subprocess.run(["bash", "-c", f'set -euo pipefail; source "$1"; {cmd}', "t", str(LIB)],
                          capture_output=True, text=True, env={**base, "LANG": "C.UTF-8", **(env or {})})


def _vars(out: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in out.splitlines() if line.startswith("HH_INSTALL_"))


PRINT = "; ".join(f'echo {v}=${{{v}:-}}' for v in ADDON_VARS)


# --- neue Installation: Zusatz-Module aus --------------------------------------------------------------------------

def test_new_install_defaults_all_addons_to_no():
    r = _run(f"hh_choices_apply_defaults; {PRINT}")
    assert r.returncode == 0, r.stderr
    assert set(_vars(r.stdout).values()) == {"no"}


def test_env_wins_over_default():
    r = _run(f"hh_choices_apply_defaults; {PRINT}", {"HH_INSTALL_VOICE": "yes"})
    v = _vars(r.stdout)
    assert v["HH_INSTALL_VOICE"] == "yes" and v["HH_INSTALL_VMS"] == "no"


def test_all_flag_restores_previous_behaviour_except_local_media():
    r = _run(f'hh_choices_parse_args --all; hh_choices_apply_defaults; {PRINT}')
    v = _vars(r.stdout)
    assert v.pop("HH_INSTALL_LOCAL_MEDIA") == "no"
    assert set(v.values()) == {"yes"}


def test_with_flag_turns_on_listed_addons_only():
    r = _run(f'hh_choices_parse_args --with=voice,vms; hh_choices_apply_defaults; {PRINT}')
    v = _vars(r.stdout)
    assert v["HH_INSTALL_VOICE"] == "yes" and v["HH_INSTALL_VMS"] == "yes"
    assert v["HH_INSTALL_SAMBA"] == "no" and v["HH_INSTALL_TAILSCALE"] == "no"


def test_with_flag_rejects_unknown_names():
    r = _run('hh_choices_parse_args --with=voice,rm_rf')
    assert r.returncode != 0 and "rm_rf" in r.stderr


def test_voice_pulls_in_containers():
    r = _run(f'hh_choices_parse_args --with=voice; hh_choices_apply_defaults; {PRINT}')
    assert _vars(r.stdout)["HH_INSTALL_CONTAINERS"] == "yes"


def test_core_parts_are_not_addons():
    """PostgreSQL und nginx sind Kern (Till 11.10.) – kein Teil der Auswahl, Standard bleibt an."""
    r = _run('hh_choices_parse_args --with=postgres')
    assert r.returncode != 0
    r = _run('hh_choices_apply_defaults; echo "P=${HH_INSTALL_POSTGRES:-unset} N=${HH_INSTALL_NGINX:-unset}"')
    assert "P=unset N=unset" in r.stdout          # nicht auf no gesetzt → Kern läuft wie bisher


# --- install.conf: eine Zeile setzen -------------------------------------------------------------------------------

def test_conf_set_replaces_or_appends_one_line(tmp_path):
    conf = tmp_path / "install.conf"
    conf.write_text("# Kopf\nHH_INSTALL_VMS='no'\nHH_INSTALL_SAMBA='no'\n")
    r = _run(f'hh_conf_set "{conf}" HH_INSTALL_VMS yes; hh_conf_set "{conf}" HH_INSTALL_VOICE yes')
    assert r.returncode == 0, r.stderr
    assert conf.read_text() == "# Kopf\nHH_INSTALL_VMS='yes'\nHH_INSTALL_SAMBA='no'\nHH_INSTALL_VOICE='yes'\n"


def test_conf_set_keeps_mode_600(tmp_path):
    conf = tmp_path / "install.conf"
    conf.write_text("HH_INSTALL_VMS='no'\n")
    conf.chmod(0o600)
    _run(f'hh_conf_set "{conf}" HH_INSTALL_VMS yes')
    assert oct(conf.stat().st_mode & 0o777) == "0o600"


def test_conf_set_refuses_foreign_keys_and_values(tmp_path):
    conf = tmp_path / "install.conf"
    conf.write_text("")
    assert _run(f'hh_conf_set "{conf}" PATH yes').returncode != 0
    assert _run(f'hh_conf_set "{conf}" HH_INSTALL_VMS "yes; rm -rf /"').returncode != 0
    assert conf.read_text() == ""


# --- update.sh: gewünscht? -----------------------------------------------------------------------------------------

def _wanted(var: str, value: str | None, installed: bool, tmp_path: Path) -> tuple[bool, str]:
    conf = tmp_path / "install.conf"
    conf.write_text("" if value is None else f"{var}='{value}'\n")
    env = {} if value is None else {var: value}
    r = _run(f'if hh_addon_wanted "{conf}" {var} {"true" if installed else "false"}; then echo JA; else echo NEIN; fi',
             env)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip().endswith("JA"), conf.read_text()


def test_installed_module_is_wanted_and_recorded_even_if_conf_said_no(tmp_path):
    """update.sh hat VMs/Container/Voice bisher trotz `no` installiert – die sind in Benutzung, nicht verwaisen lassen."""
    ok, conf = _wanted("HH_INSTALL_VMS", "no", True, tmp_path)
    assert ok and "HH_INSTALL_VMS='yes'" in conf


def test_missing_value_on_existing_server_keeps_old_default_yes(tmp_path):
    ok, conf = _wanted("HH_INSTALL_VOICE", None, False, tmp_path)
    assert ok and "HH_INSTALL_VOICE='yes'" in conf


def test_explicit_no_and_not_installed_stays_off(tmp_path):
    ok, conf = _wanted("HH_INSTALL_CONTAINERS", "no", False, tmp_path)
    assert not ok and conf == "HH_INSTALL_CONTAINERS='no'\n"


def test_explicit_yes_not_installed_is_wanted(tmp_path):
    ok, _ = _wanted("HH_INSTALL_SAMBA", "yes", False, tmp_path)
    assert ok
