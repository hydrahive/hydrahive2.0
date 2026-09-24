# AgentLink Runtime Profiles

## Was

Interne HydraHive-Handoffs erhalten ein optionales, auftragsbezogenes Runtime-Profil:
`quick`, `standard` oder `deep`. Das Profil begrenzt Iterationen, maximale
Ausgabetokens pro LLM-Aufruf und Laufzeit des delegierten Runs. Es darf die im
Ziel-Spezialisten gespeicherten Obergrenzen niemals erhöhen.

## Warum

Ein einziger globaler Wert ist für kurze Recherchen unnötig teuer und für größere
Codeaufgaben häufig zu knapp. Gleichzeitig wäre ein frei wählbares per-call Budget
eine Umgehung der administrativ gesetzten Agentengrenzen. Profile liefern daher
vorhersehbare Kosten- und Laufzeitklassen, während der Ziel-Agent die letzte
Autorität über seine Caps behält.

## Geprüfte Optionen

### A. Nur gespeicherte Agentenwerte

- Einfach und kompatibel.
- Kann kurze und tiefe Aufträge nicht unterscheiden.
- Löst das beobachtete Problem nur teilweise.

### B. Frei wählbare Zahlen pro `ask_agent`-Aufruf

- Maximale Flexibilität.
- Größere Angriffs- und Fehlkonfigurationsfläche.
- Caller könnten versehentlich oder absichtlich sehr teure Läufe anfordern.

### C. Feste Profile, am Ziel gegen gespeicherte Caps geschnitten

- Kleine, validierbare Schnittstelle.
- Der Empfänger berechnet die effektiven Werte selbst und vertraut keinen Zahlen
  aus dem Transport.
- Neue Profile benötigen eine Codeänderung.

## Entscheidung

Option C. Folgende Profilobergrenzen gelten:

| Profil | Iterationen | `max_tokens` je LLM-Aufruf | Laufzeit |
|---|---:|---:|---:|
| `quick` | 8 | 8.192 | 180 s |
| `standard` | 32 | 16.384 | 540 s |
| `deep` | 96 | 32.768 | 1.800 s |

Für jede Dimension gilt:

```text
effektiv = min(Profilobergrenze, gespeicherter Cap des Ziel-Spezialisten)
```

Fehlende oder ältere Aufrufe verwenden `standard`. Externe/föderierte Ziele
behalten das bisherige Timeout-Verhalten; HydraHive-interne Profile ändern weder
Modell noch Tools, Skills, Workspace oder Berechtigungen.

## Transport

AgentLink akzeptiert derzeit kein zusätzliches Runtime-Objekt. Interne Metadaten
werden daher versioniert im bereits etablierten maschinenlesbaren `handoff.reason`-
Präfix transportiert:

```text
hh-target:<agent-id>|hh-runtime:v1:<profile>|hh-task:<kurztext>
```

Nur der Profilname wird transportiert. Der Empfänger ignoriert unbekannte
Versionen/Profile und fällt auf `standard` zurück. Er berechnet alle effektiven
Zahlen lokal aus der aktuellen Zielkonfiguration.

Die lokale Handoff-Session speichert zusätzlich:

```json
{
  "agentlink_runtime": {
    "version": 1,
    "profile": "standard",
    "max_iterations": 32,
    "max_tokens": 16384,
    "timeout_seconds": 540
  }
}
```

Der Runner schneidet die beiden Runner-Werte erneut gegen die aktuelle
Agentenkonfiguration. Der äußere Receiver-Timeout verwendet den effektiven
`timeout_seconds`-Wert. Der Caller wartet genau diesen Wert plus 60 Sekunden, damit
eine terminale Antwort noch zugestellt werden kann.

## Sicherheitsgrenzen

- Profile können Caps ausschließlich reduzieren, nie erhöhen.
- Der Empfänger vertraut keinen transportierten Zahlen.
- Keine per-call Änderung von Modell, Fallbacks, Tools, Skills oder Rechten.
- Profilmetadaten werden nicht in den Nutzerprompt aufgenommen.
- Ungültige/fehlende Konfiguration wird sicher auf gebundene Defaults reduziert.
- Externe Handoffs können durch ein gefälschtes Profil höchstens weniger Ressourcen
  erhalten, niemals mehr.
- Spezialisten-Defaulttools bleiben eine Teilmenge der Tools des Projekt-Agenten.
- Ein Projekt-Agent besitzt bewusst Authoring-Rechte für Runtime-Caps bis zu den
  globalen Systemgrenzen. Seine eigenen Laufwerte sind kein Projekt-Quota: Sonst
  könnte ein Projekt-Agent mit 16 Iterationen keinen tieferen Spezialisten anlegen.
  Echte Kostenquoten wären eine separate administrative Projekt-Policy.

## Akzeptanzkriterien

1. `ask_agent(profile=...)` akzeptiert nur `quick|standard|deep`.
2. Interne States enthalten das versionierte Profil, keine freien Budgetzahlen.
3. Der Receiver berechnet alle effektiven Werte lokal und speichert sie in der Session.
4. Runner nutzt die effektiven Iterations- und Tokenlimits.
5. Caller-Timeout ist immer mindestens 60 Sekunden größer als Target-Timeout.
6. Profile erweitern keine Berechtigung und kein Agentenlimit.
7. Alte Handoffs ohne Profil bleiben als `standard` funktionsfähig.
8. Unit-, Receiver-, Spoofing- und Runner-Regressionstests decken Grenzen und Fallbacks ab.
