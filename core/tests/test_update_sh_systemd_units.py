"""Verhindert Rollout-Lücken: jede Trigger-Unit aus 50-systemd.sh (frischer
Install) muss auch in update.sh (Bestandsserver) angelegt werden.

Bug-Kontext: hydrahive2-migration.service/.timer wurden nur in
installer/modules/50-systemd.sh definiert (frischer Install), aber update.sh
(für bereits laufende Server) legte den Block nicht an — auf Bestandsservern
blieb der Migrations-Trigger dadurch für immer unbeachtet liegen, ohne
Fehlermeldung. Dieser Test vergleicht die *_SERVICE-Variablennamen aus
50-systemd.sh gegen die tatsächlich in update.sh geschriebenen Units.
"""
from __future__ import annotations

import re
from pathlib import Path

INSTALLER_DIR = Path(__file__).resolve().parents[2] / "installer"
FRESH_INSTALL = INSTALLER_DIR / "modules" / "50-systemd.sh"
UPDATE_SCRIPT = INSTALLER_DIR / "update.sh"

# Units, die bewusst NUR beim Frischinstall entstehen (kein Update-Pendant
# nötig) — z.B. der Haupt-Service selbst, der beim Update schon längst läuft.
EXEMPT = {"hydrahive2.service"}


def _service_units_written(text: str) -> set[str]:
    """Findet alle 'hydrahive2-*.service'/'*.timer'-Dateinamen, die per
    'cat > .../NAME <<EOF' geschrieben werden."""
    return set(re.findall(r"hydrahive2-[a-z-]+\.(?:service|timer)", text))


def test_every_fresh_install_unit_has_update_counterpart():
    fresh = _service_units_written(FRESH_INSTALL.read_text())
    updated = _service_units_written(UPDATE_SCRIPT.read_text())

    fresh -= EXEMPT
    missing = fresh - updated
    assert not missing, (
        f"Diese Trigger-Units werden bei Frischinstall angelegt, aber NICHT "
        f"bei update.sh nachgerüstet — Bestandsserver bekommen sie nie: "
        f"{sorted(missing)}"
    )


def test_migration_unit_specifically_present_in_update_sh():
    """Regression-Guard für den konkreten Fund vom 2026-07-02."""
    text = UPDATE_SCRIPT.read_text()
    assert "hydrahive2-migration.service" in text
    assert "hydrahive2-migration.timer" in text
    assert "installer/migrate.sh" in text
