"""Logging statt stillem Verschlucken (Issue #204).

Best-effort-Pfade dürfen Fehler nicht lautlos schlucken — sonst sind operative
Blindspots nicht diagnostizierbar.

Hinweis: hydrahive-Imports bewusst LAZY in den Tests. Modul-Level-Import von
llm._oauth_usage würde settings.data_dir bereits zur Collection-Zeit (vor dem
setup_test_env-Fixture) einfrieren und damit die ganze Session vergiften.
Der Health-Backfill-Teil (#203) lebt seit dem Akte-Modul-Port im Modul
(modules/patientenakte/tests/test_health_logging.py).
"""
from __future__ import annotations

import logging


# --- #204 oauth_usage cache: load/save loggen statt schlucken ----------------

def test_oauth_load_cache_logs_on_corrupt_file(client, tmp_path, monkeypatch, caplog):
    from hydrahive.llm import _oauth_usage
    bad = tmp_path / "oauth_usage.json"
    bad.write_text("{ corrupt", encoding="utf-8")
    monkeypatch.setattr(_oauth_usage, "_CACHE_FILE", bad)
    with caplog.at_level(logging.WARNING):
        result = _oauth_usage._load_cache()
    assert result == {}
    assert any("laden fehlgeschlagen" in r.message for r in caplog.records)


def test_oauth_save_cache_logs_on_write_error(client, tmp_path, monkeypatch, caplog):
    from hydrahive.llm import _oauth_usage
    # Ziel ist ein Verzeichnis → write_text wirft IsADirectoryError
    monkeypatch.setattr(_oauth_usage, "_CACHE_FILE", tmp_path)
    with caplog.at_level(logging.WARNING):
        _oauth_usage._save_cache({"x": 1})  # darf NICHT werfen
    assert any("schreiben fehlgeschlagen" in r.message for r in caplog.records)
