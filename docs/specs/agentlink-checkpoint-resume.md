# AgentLink Checkpoint and Resume

## Problem

Ein Specialist-Run kann nach vielen korrekten Arbeitsschritten am Iterationslimit
pausieren. Heute wird dieser Zustand als undifferenzierter Fehler zurückgegeben;
ein erneuter `ask_agent`-Aufruf erzeugt eine neue Session und verliert den
unmittelbaren Arbeitskontext.

## Geprüfte Optionen

### A. Automatisch weiterlaufen

- Bequem für den Caller.
- Umgeht die beabsichtigte Kosten-/Laufzeitgrenze und kann Endlosschleifen erzeugen.

### B. Kontrollierter Resume derselben Session mit Einmal-Token

- Kontext, Toolresultate und Integrity-Evidence bleiben erhalten.
- Der Caller muss die Fortsetzung ausdrücklich beauftragen.
- Benötigt gebundene, persistente Checkpoint-Referenzen.

### C. Neue Session mit textuellem Handover

- Einfacher als echte Fortsetzung.
- Verliert Details und kann bereits ausgeführte Änderungen wiederholen.

## Entscheidung

Option B. Nur Runner-Fehler mit `metadata.kind == "max_iterations"` erzeugen einen
resumierbaren Checkpoint. Timeout, Providerfehler, Shutdown und sonstige Fehler
bleiben terminal und nicht resumierbar.

## Protokoll

Die Antwort enthält neben dem begrenzten Teilergebnis einen maschinenlesbaren
Finding-Eintrag:

```text
HH_CHECKPOINT_V1:{"version":1,"reason":"max_iterations",...}
```

Das Objekt enthält:

- `resume_token`: zufällige lokale Handoff-ID, keine Session-ID als Autorisierung,
- `session_id`: Referenz für Diagnose und Arbeitsstatus,
- `reason`: `max_iterations`,
- `remaining_work`: konservative Beschreibung, dass der begonnene Auftrag noch
  abgeschlossen und verifiziert werden muss.

`ask_agent` erkennt den Marker, gibt ihn in `ToolResult.metadata.checkpoint` zurück
und nennt im Fehlertext den kontrollierten Folgeaufruf.

Ein Resume-Aufruf setzt `resume_token`. Für interne Handoffs wird er versioniert in
`handoff.reason` transportiert:

```text
hh-target:<agent>|hh-runtime:v1:<profile>|hh-resume:v1:<token>|hh-task:<text>
```

## Autorisierung und Replay-Schutz

Der Receiver nimmt einen Token nur an, wenn der persistierte Handoff:

1. den Status `paused` hat,
2. zum gleichen Ziel-Agenten gehört,
3. vom exakt gleichen AgentLink-Caller stammt.

Das Claiming erfolgt atomar und setzt den alten Eintrag auf `resumed`. Ein Token ist
nur einmal verwendbar. Der neue Handoff erhält eine neue Handoff-ID und bei einer
weiteren Pause entsprechend einen neuen Resume-Token.

## Laufverhalten

- Die bestehende Specialist-Session wird wiederverwendet.
- Der Resume-Turn lautet intern nur `weiter`, damit vorhandene Continuity-/Integrity-
  Mechanismen greifen und kein zweiter vollständiger Auftrag angehängt wird.
- Ein neues Runtime-Profil darf gewählt werden, wird aber wie immer gegen die
  gespeicherten Agenten-Caps geschnitten.
- Modell, Tools, Skills, Owner, Projekt und Workspace bleiben unverändert.
- Parallele oder wiederholte Claims werden abgelehnt.

## Arbeitsstatus

Der Checkpoint liefert mindestens Sessionbezug, Abbruchgrund, Teilergebnis und
verbleibende Arbeit. Laufende Iterations-/Tool-Aktivität bleibt über die bestehende
Session-Activity sichtbar; ein separates AgentLink-Progress-Protokoll ist nicht Teil
dieser Änderung, damit Antwort-Futures nicht durch Zwischenstates aufgelöst werden.

## Akzeptanzkriterien

1. `max_iterations` erzeugt Status `paused` statt generischem `error`.
2. Antwort enthält begrenztes Teilergebnis plus strukturierten Checkpoint.
3. `ask_agent(resume_token=...)` führt dieselbe Session fort.
4. Falscher Caller, falsches Ziel, unbekannter oder wiederverwendeter Token wird
   abgelehnt.
5. Nicht-resumierbare Fehler geben keinen Token aus.
6. Resume kann das gespeicherte Agentenlimit und seine Rechte nicht erhöhen.
7. Bestehende Handoffs ohne Resume-Metadaten bleiben kompatibel.
