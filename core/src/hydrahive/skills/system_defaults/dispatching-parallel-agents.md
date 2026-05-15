---
name: dispatching-parallel-agents
description: Sub-Agenten für unabhängige Teilprobleme parallel starten — einer pro Domäne, klare Aufgabentrennung, definierte Outputs.
when_to_use: Wenn eine Aufgabe ≥2 unabhängige Teilprobleme hat, bei paralleler Analyse (Security + Performance + Code-Review), bei Multi-File-Refactoring
tools_required: [shell_exec]
---

# Dispatching Parallel Agents

## Wann Sub-Agenten sinnvoll sind

✅ Parallel starten wenn:
- Teilprobleme unabhängig sind (kein geteilter Zustand)
- Verschiedene Expertise-Domänen gefragt sind
- Analyse-Aufgaben die nicht voneinander abhängen
- Recherche die von mehreren Blickwinkeln profitiert

❌ Nicht parallel wenn:
- Task B braucht das Ergebnis von Task A
- Beide Tasks die gleiche Datei schreiben
- Koordinationsaufwand größer als der Gewinn

## Struktur eines Sub-Agenten-Auftrags

Jeder Auftrag muss enthalten:

```
Agent: [Domänen-Name]
Aufgabe: [Was genau, 1-3 Sätze]
Input: [Welche Dateien/Daten bekommt er]
Output: [Was genau soll zurückkommen]
Scope: [Was ist explizit ausgeschlossen]
```

## Beispiel: Code-Review-Trio

```
Agent 1 — Security Review
Aufgabe: api/middleware/api_keys.py auf OWASP Top 10 prüfen
Input: Dateiinhalt
Output: Liste von Findings mit Severity (CRITICAL/HIGH/MEDIUM/LOW)
Scope: Nur Security, keine Style-Kommentare

Agent 2 — Performance Review  
Aufgabe: db/sessions.py auf N+1-Queries und fehlende Indizes prüfen
Input: Dateiinhalt + Schema
Output: Konkrete Query-Probleme mit Fix-Vorschlag
Scope: Nur Performance, kein Security

Agent 3 — Test Coverage
Aufgabe: Prüfen welche Branches in session.py nicht getestet sind
Input: session.py + tests/test_sessions.py
Output: Liste unkoverter Pfade, Priorität nach Risiko
Scope: Nur Coverage-Gaps, kein Implementierungs-Review
```

## Ausgabe-Integration

Nach Rückkehr aller Agenten:
1. Findings zusammenführen
2. Duplikate eliminieren
3. Nach Severity sortieren
4. CRITICAL/HIGH sofort angehen

## Typische Parallelisierungs-Muster

### Analyse-Muster
```
├── Agent: Security-Analyse
├── Agent: Performance-Analyse  
└── Agent: Maintainability-Analyse
    → Zusammenführen → Prioritätsliste
```

### Recherche-Muster
```
├── Agent: Ansatz A evaluieren
├── Agent: Ansatz B evaluieren
└── Agent: Ansatz C evaluieren
    → Vergleich → Empfehlung
```

### Multi-Service-Muster
```
├── Agent: Service A testen
├── Agent: Service B testen
└── Agent: Integration zwischen A+B testen
    → Alle grün? → Deploy
```

## Fokus-Regel

Ein Sub-Agent — eine Domäne. Ein Generalist-Agent der alles macht ist schlechter als drei fokussierte Agenten. Überlappende Scopes führen zu inkonsistenten Ergebnissen.
