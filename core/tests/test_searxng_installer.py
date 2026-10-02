"""SearXNG-Installer und Bestands-Migration (Spec websearch-blocked-engines §6/§7).

1. Der Installer schrieb seine Einstellungen nach /opt/searxng/searx/settings.yml —
   das ist SearXNGs mitgelieferte STANDARDDATEI (2.766 Zeilen). Neuinstallationen
   verloren so alle Standardwerte. Eigene Datei gehört nach searxng/settings.yml.
2. Am 02.10.2026 waren alle aktiven Suchanbieter gesperrt; Bing und Yandex
   funktionierten, waren aber aus. Die Migration schaltet sie im Bestand ein,
   ohne eigene Einstellungen zu zerstören.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
MODULE = INSTALLER / "modules" / "76-searxng.sh"
MIGRATION = INSTALLER / "migrations" / "searxng-engines.sh"
ENGINES_PY = INSTALLER / "lib" / "searxng_engines.py"


def test_installer_never_writes_searx_default_settings():
    text = MODULE.read_text()

    assert 'SEARXNG_SETTINGS="$SEARXNG_DIR/searxng/settings.yml"' in text
    assert 'SEARXNG_SETTINGS="$SEARXNG_DIR/searx/settings.yml"' not in text
    assert "Environment=SEARXNG_SETTINGS_PATH=$SEARXNG_SETTINGS" in text


def test_installer_only_rewrites_its_own_file():
    """Von Hand angepasste Datei (wie Prod) bleibt unangetastet."""
    text = MODULE.read_text()

    assert "# HydraHive SearXNG — automatisch generiert" in text
    guard = text.split('cat > "$SEARXNG_SETTINGS"', 1)[0]
    assert 'grep -q "^# HydraHive SearXNG — automatisch generiert" "$SEARXNG_SETTINGS"' in guard


def test_installer_restores_overwritten_default_file():
    text = MODULE.read_text()

    # safe.directory: das Repo gehört dem Nutzer searxng, der Installer läuft als root.
    assert 'git -c safe.directory="$SEARXNG_DIR" -C "$SEARXNG_DIR" checkout -- searx/settings.yml' in text
    assert "/var/backups/searxng-default-settings-" in text


def test_generated_settings_enable_working_engines_without_overriding_defaults():
    text = MODULE.read_text()
    block = text.split("<<EOFSETTINGS", 1)[1].split("EOFSETTINGS", 1)[0]
    engines = block.split("engines:", 1)[1]

    assert "- name: bing" in engines and "- name: yandex" in engines
    # Nur name + disabled, damit SearXNGs Standardfelder (shortcut, categories …) bleiben.
    assert "engine: " not in engines


def test_update_runs_engine_migration():
    assert "installer/migrations/searxng-engines.sh" in (INSTALLER / "update.sh").read_text()


# --- Python-Teil der Migration: YAML sicher ergänzen -------------------------

def _merge(tmp_path: Path, content: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    f = tmp_path / "settings.yml"
    f.write_text(content)
    r = subprocess.run([sys.executable, str(ENGINES_PY), str(f)], capture_output=True, text=True)
    return r, f


PROD_LIKE = """use_default_settings: true
server:
  port: 8888
  secret_key: "geheim-123"
  limiter: false
search:
  formats:
    - html
    - json
"""


def test_adds_bing_and_yandex_and_keeps_everything_else(tmp_path):
    r, f = _merge(tmp_path, PROD_LIKE)

    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "changed"
    d = yaml.safe_load(f.read_text())
    assert {"name": "bing", "disabled": False} in d["engines"]
    assert {"name": "yandex", "disabled": False} in d["engines"]
    assert d["server"]["secret_key"] == "geheim-123"
    assert d["search"]["formats"] == ["html", "json"]
    assert d["use_default_settings"] is True


def test_second_run_changes_nothing(tmp_path):
    _merge(tmp_path, PROD_LIKE)
    before = (tmp_path / "settings.yml").read_text()
    r = subprocess.run([sys.executable, str(ENGINES_PY), str(tmp_path / "settings.yml")], capture_output=True, text=True)

    assert r.stdout.strip() == "unchanged"
    assert (tmp_path / "settings.yml").read_text() == before


def test_respects_user_choice_for_bing(tmp_path):
    """Hat der Nutzer bing selbst ausgeschaltet, bleibt es aus."""
    content = PROD_LIKE + "engines:\n  - name: bing\n    disabled: true\n  - name: qwant\n    disabled: false\n"
    r, f = _merge(tmp_path, content)

    d = yaml.safe_load(f.read_text())
    names = [e["name"] for e in d["engines"]]
    assert {"name": "bing", "disabled": True} in d["engines"]
    assert {"name": "qwant", "disabled": False} in d["engines"]
    assert names.count("bing") == 1 and "yandex" in names


def test_existing_comments_file_is_left_alone_when_complete(tmp_path):
    """Prod nach dem Live-Fix: beide schon da → Datei byte-gleich (Kommentare bleiben)."""
    content = PROD_LIKE + "\n# Live-Fix 02.10.\nengines:\n  - name: bing\n    disabled: false\n  - name: yandex\n    disabled: false\n"
    r, f = _merge(tmp_path, content)

    assert r.stdout.strip() == "unchanged"
    assert f.read_text() == content


@pytest.mark.parametrize("bad", ["engines: [\n", "- nur\n- liste\n", "engines: 5\n"])
def test_invalid_file_is_not_touched(tmp_path, bad):
    r, f = _merge(tmp_path, bad)

    assert r.returncode != 0
    assert f.read_text() == bad


def test_shell_migration_backs_up_and_verifies(tmp_path):
    text = MIGRATION.read_text()

    assert "SEARXNG_SETTINGS_PATH" in text                       # Pfad aus der Unit
    assert "/var/backups/searxng-settings-" in text              # Sicherung vor Änderung
    assert "format=json" in text and "results" in text           # echte Suche danach
    assert 'cp -a "$backup" "$settings"' in text                 # Rücksprung bei 0 Treffern
