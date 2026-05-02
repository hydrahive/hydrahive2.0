SUMMARY_INSTRUCTIONS = """\
Du erstellst eine strukturierte Zusammenfassung der bisherigen Konversation
in genau dem unten angegebenen Markdown-Format. Halluzinieren ist verboten —
nur Fakten aus dem Input. Schreibe knapp und konkret.

Format (genau diese Headings, in dieser Reihenfolge):

## Goal
[Was der User erreichen möchte]

## Constraints & Preferences
- [Anforderungen, Wünsche, technische Vorgaben]

## Progress
### Done
- [x] [Erledigte Aufgaben]

### In Progress
- [ ] [Aktuell laufende Arbeit]

### Blocked
- [Blocker, falls vorhanden]

## Key Decisions
- **[Entscheidung]**: [Begründung]

## Next Steps
1. [Was als nächstes gemacht werden sollte]

## Critical Context
- [Daten/Variablen/Pfade die zum Weiterarbeiten nötig sind]

<read-files>
[ein Pfad pro Zeile, gelesene Dateien]
</read-files>

<modified-files>
[ein Pfad pro Zeile, geänderte Dateien]
</modified-files>
"""

MERGE_INSTRUCTIONS = """\
Mehrere Teil-Zusammenfassungen einer langen Konversation liegen vor. Merge
sie zu einer einzigen kohärenten Zusammenfassung im selben Markdown-Format
wie die Eingaben. Kombiniere Goals/Constraints/Decisions ohne Duplikate.
Progress chronologisch — späteres überschreibt frühere Statements (Done aus
Chunk 5 hat Vorrang vor In Progress aus Chunk 2 wenn dasselbe Item).
Halluzinieren verboten — nur Fakten aus den Inputs.
"""
