"""update.sh bindet die Systemupdates ein (docs/specs/system-updates.md, Task f24c39bf)."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UPDATE = REPO / "installer" / "update.sh"
INSTALL = REPO / "installer" / "install.sh"


def _code(path: Path) -> str:
    return "\n".join(l for l in path.read_text().splitlines() if not l.lstrip().startswith("#"))


def test_update_laedt_und_ruft_system_upgrade() -> None:
    text = _code(UPDATE)
    assert 'source "$HH_REPO_DIR/installer/lib/system-upgrade.sh"' in text
    assert re.search(r"^hh_ensure_auto_updates$", text, re.M)
    assert re.search(r"^hh_system_upgrade \|\| hh_warn ", text, re.M)


def test_nach_selbstheilung_vor_node() -> None:
    """DNS muss gehen (Selbstheilung); die automatischen Updates werden vor Node.js eingerichtet."""
    text = _code(UPDATE)
    dns = text.index("hh_verify_dns")
    auto = re.search(r"^hh_ensure_auto_updates$", text, re.M).start()
    node = text.index('log "Node.js prüfen"')
    assert dns < auto < node


def test_vollupgrade_erst_nach_bestandener_pruefung() -> None:
    """update-rollback.md F9: das nicht umkehrbare apt-Vollupgrade läuft erst nach Phase C, nie vor einem Rückweg."""
    text = _code(UPDATE)
    ok = re.search(r"^hh_safety_mark_ok$", text, re.M).start()
    upg = re.search(r"^hh_system_upgrade \|\| hh_warn ", text, re.M).start()
    assert len(re.findall(r"^hh_system_upgrade\b", text, re.M)) == 1
    assert ok < upg


def test_install_schaltet_auto_updates_ein() -> None:
    text = _code(INSTALL)
    assert 'source "$INSTALLER_DIR/lib/system-upgrade.sh"' in text
    assert re.search(r"^hh_ensure_auto_updates$", text, re.M)
