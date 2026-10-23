"""Hilfe-Assistent: Handbuch laden und durchsuchen (docs/plans/help-assistant.md, Etappe 1, Schritt 1).

Quellen: Hilfe-Artikel frontend/src/i18n/help/<lang>/<topic>.md und docs/USER_GUIDE.md (Topic „guide“).
Sprache des Nutzers zuerst, sonst Deutsch, sonst Englisch – wie loadHelp() im Frontend.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.helpdesk import _manual as manual


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    help_dir = tmp_path / "frontend" / "src" / "i18n" / "help"
    (help_dir / "de").mkdir(parents=True)
    (help_dir / "en").mkdir(parents=True)
    (help_dir / "de" / "agents.md").write_text(
        "# Agenten\n\nEin Agent ist eine Konfiguration.\n\n## Neuen Agent anlegen\n\n"
        "Klicke auf „Neuer Agent“ und wähle ein Modell.\n")
    (help_dir / "en" / "agents.md").write_text("# Agents\n\nAn agent is a configuration.\n")
    (help_dir / "de" / "llm.md").write_text("# KI-Modelle\n\n## Provider hinzufügen\n\nAPI-Schlüssel eintragen.\n")
    (help_dir / "en" / "containers.md").write_text("# Containers\n\nOnly in English.\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "USER_GUIDE.md").write_text("# Handbuch\n\n## Erste Schritte\n\nAnmelden und Agent anlegen.\n")
    monkeypatch.setattr(manual, "REPO_ROOT", tmp_path)
    manual.clear_cache()
    return tmp_path


def test_topics_lists_articles_and_guide(repo):
    assert manual.topics("de") == ["agents", "containers", "guide", "llm"]


def test_read_prefers_user_language(repo):
    assert manual.read("agents", "en").startswith("# Agents")
    assert manual.read("agents", "de").startswith("# Agenten")


def test_read_falls_back_to_german_then_english(repo):
    assert manual.read("llm", "en").startswith("# KI-Modelle")          # nur DE vorhanden
    assert manual.read("containers", "de").startswith("# Containers")   # nur EN vorhanden


def test_read_language_code_with_region(repo):
    assert manual.read("agents", "en-US").startswith("# Agents")


def test_read_guide_is_user_guide(repo):
    assert manual.read("guide", "de").startswith("# Handbuch")


def test_read_unknown_topic_is_none(repo):
    assert manual.read("gibtsnicht", "de") is None


@pytest.mark.parametrize("evil", ["../../etc/passwd", "../de/agents", "agents/../../x", "/etc/passwd", "", "a" * 200])
def test_read_rejects_paths(repo, evil):
    """Nur bekannte Topic-Namen – nie einen Pfad aus dem Modell ins Dateisystem durchreichen."""
    assert manual.read(evil, "de") is None


def test_read_rejects_language_paths(repo):
    """Auch die Sprache kommt von außen – kein Pfad daraus. Datei außerhalb der Hilfe darf nie gelesen werden."""
    secret = repo / "frontend" / "src" / "i18n" / "geheim"
    secret.mkdir()
    (secret / "agents.md").write_text("GEHEIM")
    assert manual.read("agents", "../geheim") .startswith("# Agenten")
    assert manual.read("agents", "../../etc").startswith("# Agenten")


def test_search_finds_section_with_heading_and_excerpt(repo):
    hits = manual.search("Agent anlegen", "de")
    assert hits[0]["topic"] == "agents"
    assert hits[0]["heading"] == "Neuen Agent anlegen"
    assert "Neuer Agent" in hits[0]["excerpt"]


def test_search_ranks_more_matching_words_first(repo):
    hits = manual.search("Agent anlegen Modell", "de")
    assert [h["topic"] for h in hits][:2] == ["agents", "guide"]


def test_search_case_and_umlaut_insensitive(repo):
    assert manual.search("PROVIDER HINZUFÜGEN", "de")[0]["topic"] == "llm"


def test_search_limit_and_empty_query(repo):
    assert len(manual.search("agent", "de", limit=1)) == 1
    assert manual.search("   ", "de") == []
    assert manual.search("xyzunbekannt", "de") == []


def test_search_excerpt_is_short(repo, monkeypatch):
    long = "Wort " * 2000
    (repo / "frontend" / "src" / "i18n" / "help" / "de" / "lang.md").write_text(f"# Lang\n\n{long}\n")
    manual.clear_cache()
    hit = manual.search("Wort", "de")[0]
    assert len(hit["excerpt"]) <= manual.EXCERPT_CHARS + 1


def test_real_manual_is_found():
    """Im echten Repo: alle Hilfe-Artikel und das Handbuch sind da."""
    manual.clear_cache()
    topics = manual.topics("de")
    assert "agents" in topics and "llm" in topics and "guide" in topics
    assert len(topics) >= 40
