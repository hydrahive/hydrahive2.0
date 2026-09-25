"""STT-Inferenz-Tuning: int8 + beam-size 1 statt float32.

Gemessen auf Ryzen 5 4500, 21,6s Diktat, Modell 'medium':
float32/beam5 = 20,5s → int8/beam1 = 9,7s. Die Flags dürfen weder im
Installer noch in der Bestandsmigration verloren gehen.
"""
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
SCRIPT = INSTALLER / "modules" / "55-voice.sh"
UPDATE_SCRIPT = INSTALLER / "update.sh"
MIGRATION = INSTALLER / "migrations" / "voice-stt-perf.sh"


def test_installer_starts_whisper_with_int8() -> None:
    """float32 auf CPU kostet das Doppelte bei gleicher Qualität."""
    text = SCRIPT.read_text()

    assert "--compute-type int8" in text
    assert "--beam-size 1" in text


def test_installer_prompt_covers_dictation_and_smarthome() -> None:
    """Der Prompt lenkt Whisper — Smart-Home-only verhunzt Code-Diktat."""
    text = SCRIPT.read_text()

    assert "--initial-prompt" in text
    assert "ffmpeg" in text
    assert "commit" in text


def test_migration_is_idempotent() -> None:
    """Mehrfachlauf darf die Unit nicht wiederholt umschreiben."""
    text = MIGRATION.read_text()

    assert 'grep -q -- "--compute-type"' in text
    assert "STT-Tuning bereits aktiv" in text


def test_migration_preserves_configured_model() -> None:
    """Wer auf 'medium' gewechselt ist, darf nicht auf 'small' zurückfallen.

    'medium' erkennt Fachbegriffe (ffmpeg, pytest, branch) deutlich
    zuverlässiger — ein stiller Downgrade wäre ein Qualitätsverlust.
    """
    text = MIGRATION.read_text()

    assert "--model[= ]" in text
    assert 'model="small"' in text  # Fallback nur wenn nichts gefunden
    assert "${HH_MODEL}" in text


def test_migration_preserves_configured_language() -> None:
    """Ein auf 'de' gepinnter Container darf nicht auf Auto-Detect fallen."""
    text = MIGRATION.read_text()

    assert "--language[= ]" in text
    assert "${HH_LANG_FLAG}" in text


def test_migration_restarts_container_not_just_service() -> None:
    """`systemctl restart` reicht im unprivilegierten LXC nicht.

    Real aufgetreten: systemd kann die cgroup des alten Prozesses nicht
    killen ("Failed to kill control group: Permission denied"). Der alte
    Whisper hält Port 10300, der neue crasht in einer Restart-Schleife an
    "address already in use" — und die ALTE Unit läuft unbemerkt weiter.
    """
    text = MIGRATION.read_text()

    assert 'incus restart "$CT_NAME"' in text
    assert "systemctl restart wyoming-whisper.service" not in text


def test_migration_verifies_new_flags_not_just_port() -> None:
    """Ein reiner Port-Check bestätigt den überlebenden alten Prozess.

    Genau dieser Fehler hat die erste Migration fälschlich "ok" melden
    lassen, obwohl weiter float32 lief.
    """
    text = MIGRATION.read_text()

    assert "pgrep -af wyoming-faster-whisper" in text
    assert 'grep -q -- "--compute-type int8"' in text


def test_migration_rolls_back_when_service_stays_down() -> None:
    """Kaputtes STT ist schlimmer als langsames STT."""
    text = MIGRATION.read_text()

    assert ".pre-perf" in text
    assert "Rollback" in text
    assert "exit 1" in text


def test_migration_skips_cleanly_without_container() -> None:
    """Hosts ohne Voice-Stack dürfen am Update nicht scheitern."""
    text = MIGRATION.read_text()

    assert "nichts zu tun" in text
    assert "exit 0" in text


def test_update_runs_stt_perf_migration() -> None:
    """55-voice.sh schreibt die Unit nur bei Neuanlage — Bestand braucht
    den expliziten Migrationsaufruf."""
    text = UPDATE_SCRIPT.read_text()

    assert "installer/migrations/voice-stt-perf.sh" in text
