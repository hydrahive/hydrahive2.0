---
name: verification-before-completion
description: 5-Schritt-Gate bevor eine Aufgabe als "fertig" gilt — frische Ausführung, Ausgabe lesen, Resultat verifizieren.
when_to_use: Vor jeder "fertig"-Meldung, bevor Tests als bestanden gemeldet werden, bevor Code als funktionierend bezeichnet wird
tools_required: [shell_exec, file_read]
---

# Verification Before Completion

## Die Regel

**Niemals "fertig" sagen ohne frischen Beweis.** Kein Hedging, kein "sollte funktionieren".

## 5-Schritt-Gate

### Schritt 1: Identifizieren
Was genau muss verifiziert werden?
- Welche Tests müssen grün sein?
- Welche Ausgabe beweist Korrektheit?
- Welcher Endpoint / welche Funktion wird geprüft?

### Schritt 2: Ausführen
Den Beweis-Befehl frisch ausführen. Nicht aus dem Cache nehmen, nicht aus der Erinnerung.

```bash
# Beispiel: Tests ausführen
pytest tests/test_feature.py -v

# Beispiel: Endpoint testen
curl -s http://localhost:8000/api/endpoint | jq .

# Beispiel: Datei-Zustand prüfen
cat /var/log/hydrahive2/app.log | tail -20
```

### Schritt 3: Ausgabe lesen
Die komplette Ausgabe lesen. Nicht überfliegen.
- Exit-Code?
- Fehlermeldungen auch wenn der Haupt-Output gut aussieht?
- Warnings die auf zukünftige Probleme hinweisen?

### Schritt 4: Gegen Erwartung verifizieren
Stimmt die Ausgabe mit dem überein was erwartet wurde?

| Erwartung | Tatsächlich | Status |
|-----------|-------------|--------|
| 5 Tests grün | 5 grün, 0 rot | ✅ |
| HTTP 200 | HTTP 200, Body korrekt | ✅ |
| Log-Eintrag vorhanden | Nicht gefunden | ❌ |

### Schritt 5: Erst jetzt melden
Wenn alle Checks bestanden: "Fertig, verifiziert durch: [konkreter Beweis]."
Wenn ein Check fehlschlägt: Debug, fix, zurück zu Schritt 2.

## Verbotene Sprache

Diese Formulierungen sind ohne frischen Beweis verboten:
- "sollte funktionieren"
- "müsste fertig sein"
- "wahrscheinlich korrekt"
- "ich glaube das geht"
- "ich habe das getestet" (ohne Ausgabe zu zeigen)

## Ausgabe-Format bei Abschluss

```
✅ Verifiziert: [Was getestet wurde]
Beweis: [Konkrete Ausgabe oder Exit-Code]
```

```
❌ Nicht bereit: [Was fehlschlägt]
Nächster Schritt: [Wie das behoben wird]
```
