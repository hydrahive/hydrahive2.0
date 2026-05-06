---
name: hh-review
description: HydraHive2-spezifischer Code-Review. Prüft Einhaltung der CLAUDE.md-Regeln — Dateigröße, Co-location, Architektur, keine print()-Statements, Settings-Singleton, keine zirkulären Imports.
when_to_use: Vor jedem Commit oder PR auf HydraHive2-Code. Prüft strukturelle Integrität des Projekts nach den verbindlichen Architektur-Regeln.
tools_required: [read_file, grep, glob, bash]
---

# HydraHive2 Code-Review

Prüfe den Code gegen die verbindlichen Regeln aus CLAUDE.md.

## 1. Dateigröße — max ~200 Zeilen

```bash
find core/src/hydrahive -name "*.py" | xargs wc -l | sort -rn | awk '$1 > 200 {print}'
find frontend/src -name "*.tsx" -o -name "*.ts" | xargs wc -l | sort -rn | awk '$1 > 200 {print}'
```

Jede Datei über 200 Zeilen ist ein Kandidat zum Aufteilen.

## 2. Co-location — Feature-Folder-Struktur

```bash
# Chat-Logik muss in features/chat/ liegen
find frontend/src/features/chat -type f | sort

# Nichts Chat-spezifisches außerhalb
grep -r "useChat\|chatApi" frontend/src/components/ 2>/dev/null
grep -r "useChat\|chatApi" frontend/src/hooks/ 2>/dev/null
```

## 3. Keine hardcodierten Pfade

```bash
grep -rn '"/home\|"/opt\|"/var\|"/tmp' core/src/hydrahive/ --include="*.py" | grep -v "test\|#\|settings"
```

Alle Pfade über `settings.*` — nie direkt hardcodieren.

## 4. Keine zirkulären Imports

```bash
cd core && python3 -c "
from hydrahive.api.routes import agents
from hydrahive.runner import runner
from hydrahive.agentlink import handoff_receiver
print('OK')
" 2>&1
```

## 5. Keine print()-Statements

```bash
grep -rn "^\s*print(" core/src/hydrahive/ --include="*.py" | grep -v "test\|#"
```

Nur `logging.getLogger(__name__).xxx()` im Produktions-Code.

## 6. Fehlerbehandlung nur an System-Grenzen

```bash
# try/except sollte nur in API-Routes, Tools und externen Clients stehen
grep -rn "try:\|except " core/src/hydrahive/ --include="*.py" -l | grep -v "api/routes\|tools\|oauth\|agentlink/client\|test"
```

## 7. AgentLink-Isolation

```bash
# AgentLink-Imports nur in agentlink/ und routes/agentlink.py
grep -rn "from hydrahive.agentlink" core/src/hydrahive/ --include="*.py" | grep -v "agentlink/\|routes/agentlink\|lifespan"
```

## 8. LLM-Provider-Konfiguration

- Anthropic + MiniMax: Modell-IDs OHNE Provider-Prefix
- Alle anderen: MIT Provider-Prefix (z.B. `openai/gpt-4o`)

## 9. Review-Bericht

```markdown
# HH2 Code-Review — [Datei/Feature]

## Verletzungen (müssen gefixt werden)
- [ ] [datei.py:23] Datei hat 340 Zeilen → aufteilen
- [ ] [utils.py:5] print() statt logging

## Warnungen
- [ ] [runner.py] Zwei Verantwortungen erkannt

## OK
- Keine zirkulären Imports
- Keine hardcodierten Pfade

## Empfehlung
[Konkrete nächste Schritte]
```
