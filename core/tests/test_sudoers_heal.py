"""Bestandsmigration: alte `Defaults:<user> !requiretty`-Zeile aus der Extensions-sudoers-Datei entfernen (Task ddec8288).

sudo-rs (Standard ab Ubuntu 26.04) kennt `requiretty` nicht. Geprüft mit sudo-rs 0.2.13: `visudo -c` lehnt die Datei ab,
jeder sudo-Aufruf meldet „unknown setting“; laut Prod-Upgrade vom 20.08. hat eine frühere Version die ganze Datei
verworfen (Extensions, Tailscale-Operator, Portfreigaben ohne sudo). 50-systemd.sh schreibt die Zeile seit 39ecfca6 nicht
mehr, aber update.sh hat bestehende Dateien nie angefasst.

Echtes bash gegen eine Datei in tmp_path; `visudo` ist ein Ersatz, der annimmt/ablehnt und mitschreibt.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parents[2] / "installer" / "lib" / "sudoers-heal.sh"
UPDATE = Path(__file__).resolve().parents[2] / "installer" / "update.sh"

OLD = (
    "# Extensions-Manager\n"
    "Defaults:hydrahive !requiretty\n"
    "hydrahive ALL=(ALL) NOPASSWD: /bin/bash\n"
    "hydrahive ALL=(ALL) NOPASSWD: /usr/bin/bash\n"
)
NEW = (
    "# Extensions-Manager\n"
    "hydrahive ALL=(ALL) NOPASSWD: /bin/bash\n"
    "hydrahive ALL=(ALL) NOPASSWD: /usr/bin/bash\n"
)


@pytest.fixture
def box(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "visudo.calls"
    visudo = bin_dir / "visudo"
    visudo.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$*" >> "{calls}"\n'
        # Ersatz: lehnt ab, wenn VISUDO_REJECT gesetzt ist oder noch eine aktive requiretty-Zeile drin ist.
        'f="${@: -1}"\n'
        '[ -n "${VISUDO_REJECT:-}" ] && exit 1\n'
        # Nur die exakte eigene Zeile gilt hier als ungültig: Der Ersatz prüft, ob die MIGRATION richtig schneidet.
        # (Echtes sudo-rs lehnt auch Varianten wie „!requiretty, env_reset“ ab – die fasst die Migration bewusst nicht
        # an; das echte Verhalten prüft der Container-Test.)
        "grep -Eq '^[[:space:]]*Defaults:hydrahive[[:space:]]+!requiretty[[:space:]]*(#.*)?$' \"$f\" && exit 1\n"
        "exit 0\n"
    )
    visudo.chmod(0o755)
    target = tmp_path / "hydrahive2-extensions"

    def run(*, user: str = "hydrahive", **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-c", f'set -euo pipefail; log() {{ echo "LOG: $*"; }}; source "$1"; hh_fix_sudoers_requiretty "{target}" "{user}"',
             "t", str(HELPER)],
            capture_output=True, text=True, timeout=20,
            env={"PATH": f"{bin_dir}:/usr/bin:/bin", **env},
        )

    return target, calls, run


def _write(target: Path, text: str, mode: int = 0o440) -> None:
    target.write_text(text)
    target.chmod(mode)


def test_old_line_is_removed_rest_unchanged(box):
    target, _, run = box
    _write(target, OLD)
    r = run()
    assert r.returncode == 0, r.stderr
    assert target.read_text() == NEW
    assert "requiretty" in r.stdout          # sichtbar im Update-Log


def test_mode_stays_0440(box):
    target, _, run = box
    _write(target, OLD)
    run()
    assert stat.S_IMODE(target.stat().st_mode) == 0o440


def test_file_without_the_line_is_untouched(box):
    target, calls, run = box
    _write(target, NEW)
    mtime = target.stat().st_mtime_ns
    r = run()
    assert r.returncode == 0, r.stderr
    assert target.read_text() == NEW and target.stat().st_mtime_ns == mtime
    assert not calls.exists()                # nicht einmal geprüft – nichts zu tun


def test_missing_file_is_fine(box):
    target, _, run = box
    r = run()
    assert r.returncode == 0, r.stderr
    assert not target.exists()


def test_rejected_by_visudo_keeps_the_old_file(box):
    """Nimmt visudo die bereinigte Fassung nicht an, bleibt die alte Datei – lieber Warnung als kaputte sudoers."""
    target, _, run = box
    _write(target, OLD)
    r = run(VISUDO_REJECT="1")
    assert r.returncode == 0, r.stderr       # Update läuft weiter
    assert target.read_text() == OLD
    assert "WARNUNG" in r.stdout
    leftovers = [p.name for p in target.parent.iterdir() if target.name in p.name and p != target]
    assert leftovers == []                   # keine Kopie (.hydrahive2-extensions.XXXX) neben der Datei


def test_candidate_is_checked_before_replace(box):
    target, calls, run = box
    _write(target, OLD)
    run()
    args = calls.read_text().split()
    assert args[:2] == ["-c", "-f"]
    assert args[2] != str(target)            # geprüft wird die Kopie, nicht die Datei selbst


@pytest.mark.parametrize("variant", [
    "Defaults:hydrahive    !requiretty",
    "Defaults:hydrahive !requiretty   ",
    "Defaults:hydrahive !requiretty # alt",
])
def test_spacing_variants_are_removed(box, variant):
    target, _, run = box
    _write(target, f"{variant}\nhydrahive ALL=(ALL) NOPASSWD: /bin/bash\n")
    assert run().returncode == 0
    assert "requiretty" not in target.read_text()


def test_only_the_own_requiretty_line_goes(box):
    """Andere Defaults-Zeilen des Nutzers und Kommentare bleiben; nur `Defaults:<user> !requiretty` fällt weg."""
    target, _, run = box
    text = ("# Defaults:hydrahive !requiretty (alt, Kommentar bleibt)\n"
            "Defaults:hydrahive env_keep += \"HOME\"\n"
            "Defaults:hydrahive !requiretty\n"
            "hydrahive ALL=(ALL) NOPASSWD: /bin/bash\n")
    _write(target, text)
    assert run().returncode == 0
    assert target.read_text() == ("# Defaults:hydrahive !requiretty (alt, Kommentar bleibt)\n"
                                  "Defaults:hydrahive env_keep += \"HOME\"\n"
                                  "hydrahive ALL=(ALL) NOPASSWD: /bin/bash\n")


def test_line_of_another_user_is_not_removed(box):
    """Mit eigener Zeile daneben: die eigene fällt, die fremde bleibt (visudo nimmt die Fassung an)."""
    target, _, run = box
    _write(target, "Defaults:anderer !requiretty\nDefaults:hydrahive !requiretty\nhydrahive ALL=(ALL) NOPASSWD: /bin/bash\n")
    assert run().returncode == 0
    assert target.read_text() == "Defaults:anderer !requiretty\nhydrahive ALL=(ALL) NOPASSWD: /bin/bash\n"


@pytest.mark.parametrize("keep", [
    "Defaults:hydrahive !requiretty, env_reset",           # mehr als nur requiretty → nicht anfassen
    "Defaults:hydrahive !requiretty_extra",                # anderes Wort
    "# Defaults:hydrahive !requiretty",                    # Kommentar
    "Defaults:hydrahive2 !requiretty",                     # anderer Nutzer mit gleichem Anfang
    "Defaults:xhydrahive !requiretty",                     # anderer Nutzer mit gleichem Ende
])
def test_lines_that_are_not_exactly_ours_stay(box, keep):
    target, _, run = box
    _write(target, f"{keep}\nDefaults:hydrahive !requiretty\nhydrahive ALL=(ALL) NOPASSWD: /bin/bash\n")
    assert run().returncode == 0
    assert target.read_text() == f"{keep}\nhydrahive ALL=(ALL) NOPASSWD: /bin/bash\n"


def test_update_sh_runs_the_fix_for_the_extensions_file():
    text = UPDATE.read_text()
    assert 'source "$HH_REPO_DIR/installer/lib/sudoers-heal.sh"' in text
    assert 'hh_fix_sudoers_requiretty /etc/sudoers.d/hydrahive2-extensions "$HH_USER"' in text


def test_helper_is_valid_bash():
    r = subprocess.run(["bash", "-n", str(HELPER)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert os.access(HELPER, os.R_OK)
