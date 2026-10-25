"""update.sh pflegt nur gewünschte Zusatz-Module (docs/specs/installer-core-first.md §2).

Vorher installierte update.sh VMs, Container und Voice bei JEDEM Update nach, sobald sie fehlten – egal, was in
install.conf stand. Ein bei der Installation abgewähltes Modul käme so beim nächsten Update wieder.
Das Verhalten von hh_addon_wanted selbst testet test_install_choices.py echt; hier: update.sh ruft es vor jedem Modul.
"""
from __future__ import annotations

import re
from pathlib import Path

UPDATE = Path(__file__).resolve().parents[2] / "installer" / "update.sh"


def _text() -> str:
    return UPDATE.read_text()


def _guard_before(call: str) -> str:
    """Die nächste umschließende if-Zeile oberhalb des Modul-Aufrufs."""
    t = _text()
    i = t.index(call)
    return t[:i].rsplit("\nif ", 1)[1].split("\n", 1)[0]


def test_update_sources_the_shared_choices_lib():
    assert 'source "$HH_REPO_DIR/installer/lib/install-choices.sh"' in _text()


def test_vms_only_when_wanted():
    assert "hh_addon_wanted" in _guard_before('bash "$HH_REPO_DIR/installer/modules/65-vms.sh"')
    assert "HH_INSTALL_VMS" in _guard_before('bash "$HH_REPO_DIR/installer/modules/65-vms.sh"')


def test_containers_only_when_wanted():
    g = _guard_before('bash "$HH_REPO_DIR/installer/modules/70-containers.sh"')
    assert "hh_addon_wanted" in g and "HH_INSTALL_CONTAINERS" in g


def test_voice_only_when_wanted():
    t = _text()
    call = 'bash "$HH_REPO_DIR/installer/modules/55-voice.sh" || log "voice-setup failed'
    before = t[:t.index(call)]
    assert "hh_addon_wanted" in before[before.rindex("voice_ok=1"):] or \
        re.search(r'hh_addon_wanted "\$INSTALL_CONF" HH_INSTALL_VOICE', before[-3000:])


def test_whatsapp_only_when_wanted():
    g = _guard_before('log "WhatsApp-Bridge: npm ci"')  # seit Task cabd0df1 npm ci statt npm install
    assert "hh_addon_wanted" in g and "HH_INSTALL_WHATSAPP" in g


def test_tailscale_only_when_wanted():
    g = _guard_before('bash "$HH_REPO_DIR/installer/modules/80-tailscale.sh"')
    assert "hh_addon_wanted" in g and "HH_INSTALL_TAILSCALE" in g


def test_installed_detection_per_module_matches_spec():
    """„Installiert“ (Spec §2): qemu / incus / Container hydrahive2-stt / node_modules der Bridge / tailscale."""
    t = _text()
    assert re.search(r'hh_addon_wanted "\$INSTALL_CONF" HH_INSTALL_VMS "\$vms_installed"', t)
    assert re.search(r'hh_addon_wanted "\$INSTALL_CONF" HH_INSTALL_CONTAINERS "\$\(hh_has incus\)"', t)
    assert re.search(r'hh_addon_wanted "\$INSTALL_CONF" HH_INSTALL_TAILSCALE "\$\(hh_has tailscale\)"', t)
    assert 'hydrahive2-stt' in t and 'node_modules' in t


def test_postgres_and_core_unchanged():
    """PostgreSQL ist Kern: weiterhin gepflegt, solange nicht ausdrücklich HH_INSTALL_POSTGRES=no."""
    assert 'if [ "${HH_INSTALL_POSTGRES:-yes}" != "no" ]; then' in _text()


def test_choices_library_loaded_after_git_pull():
    """Echter Fund auf hydratest (11.10.2026): Die Bibliothek wurde vor git pull geladen – eine Änderung nur an ihr
    (ohne update.sh-Änderung, also ohne re-exec) griff erst beim nächsten Update."""
    src = UPDATE.read_text()
    assert src.index('source "$HH_REPO_DIR/installer/lib/install-choices.sh"') > src.index('exec bash "$SELF_PATH"')


def test_vms_installed_means_vm_manager_not_just_qemu():
    """Echter Fund (hh-instcore, 11.10.2026): incus zieht qemu-system-x86 als Abhängigkeit mit. „qemu vorhanden“ machte
    nach einer Container-Installation die VMs zu „installiert“ → update.sh setzte VMS=yes und richtete den VM-Manager
    ein, obwohl er abgewählt war. Merkmal ist die Unit, die nur 65-vms.sh anlegt."""
    t = _text()
    line = next(x for x in t.splitlines() if x.startswith("vms_installed=false"))
    assert "/etc/systemd/system/hydrahive2-websockify.service" in line
    assert "qemu-system-x86_64" in line
    assert "hh_has qemu-system-x86_64)\"" not in _guard_before("installer/modules/65-vms.sh")


def test_voice_ok_needs_a_real_whisper_answer():
    """Echter Fund (hydratest, 11.10.2026): STT-Container ohne Whisper, aber der incus-Proxy lauscht auf 10300 →
    `ss` meldete „hört“, update.sh hielt Voice für in Ordnung und reparierte nie. Bedingung 4 fragt jetzt den Dienst."""
    t = _text()
    block = t[t.index("voice_ok=1"):t.index("voice_installed=false")]
    assert 'ss -tln 2>/dev/null | grep -q "127.0.0.1:10300"' not in block
    assert '"type": "describe"' in block and '"type": "info"' in block
