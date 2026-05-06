---
name: docs
description: Generiert Dokumentation, API-Docs, README-Dateien und Code-Kommentare. Für neue Doku oder nachträgliches Dokumentieren von bestehendem Code.
when_to_use: Wenn der User Dokumentation schreiben oder verbessern will, Docstrings nachträglich hinzufügen möchte, ein README oder eine Architektur-Beschreibung braucht.
tools_required: [read_file, write_file, grep, glob]
---

# Dokumentations-Skill

## 1. Python Docstrings

```python
def calculate_total(items, tax_rate=0.08):
    """
    Calculate total price including tax.

    Args:
        items (list): Items with price and quantity.
        tax_rate (float): Tax rate. Defaults to 0.08.

    Returns:
        float: Total price including tax.

    Raises:
        ValueError: If items is empty or tax_rate is negative.

    Example:
        >>> calculate_total([{'price': 10, 'qty': 2}])
        21.6
    """
```

## 2. README-Template

```markdown
# Projektname

Kurze Beschreibung was das Projekt macht.

## Installation
\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Konfiguration

| Variable | Beschreibung |
|----------|-------------|
| `HH_DATA_DIR` | Datenpfad |
| `HH_AGENTLINK_URL` | AgentLink-URL |

## Architektur

Übersicht der Komponenten.
```

## 3. Architektur-Doku

```markdown
# Architektur

## Überblick
Komponenten: Frontend (React) · Backend (FastAPI) · DB (SQLite)

## Datenfluss
1. User-Request → Frontend
2. Frontend → REST-API
3. API validiert + verarbeitet
4. DB wird aktualisiert
5. Antwort zurück

## Wichtige Entscheidungen
- Warum SQLite: kein Infra-Overhead, single-node
- Warum FastAPI: async, typisiert, Auto-Docs
```

## 4. Changelog-Format

```markdown
# Changelog

## [Unreleased]

## [1.2.0] - 2026-05-07

### Added
- Feature X

### Changed
- Y verbessert

### Fixed
- Bug in Z
```

## 5. Strategie für nachträgliche Dokumentation

1. Datei lesen — verstehen was sie tut
2. WHY dokumentieren, nicht WHAT (Namen erklären das schon)
3. Modul-Docstring: Zweck + Haupt-Einstiegspunkte
4. Funktion-Docstrings: args, returns, raises, überraschendes Verhalten
5. Inline nur bei nicht-offensichtlicher Logik

## Wann nutzen

Wenn Docstrings fehlen, READMEs veraltet sind, Architektur-Entscheidungen nicht dokumentiert sind oder API-Specs gebraucht werden.
