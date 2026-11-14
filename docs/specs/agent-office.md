# Agenten-Büro

Eigene Seite `/office` (Nav-Gruppe „overview“): zeigt live alle laufenden Agenten über alle Projekte,
wer wen beauftragt hat, wie weit der Auftrag ist, und auf Klick den echten Tool-Verlauf. Löst das
Problem „Spezialist läuft im Hintergrund, bis zum Timeout sieht man nichts" (Till, 14.11.2026).

Das bestehende Pixel-Fenster im Chat (`/pixel`-Befehl, `AgentPixelMonitor.tsx`) bleibt unverändert
bestehen — es wird in einer späteren Etappe repariert (`interacting`-Linien werden nie gesetzt), ist
aber nicht Teil dieser Spec.

## 1. Datenmodell (Backend, keine neue Tabelle)

`runner/activity.py` kennt heute nur `current_tool: str | None`. Erweitern um:

```python
@dataclass
class AgentActivity:
    session_id: str
    agent_id: str
    name: str
    owner: str
    project_id: str | None
    current_tool: str | None
    started_at: float
    # NEU:
    parent_session_id: str | None   # Session des Auftraggebers, falls Delegation
    delegation_id: str | None       # agent_delegations.id, falls vorhanden
    iteration: int                  # aktueller Schleifen-Durchlauf
    max_iterations: int             # aus RunSettings (Template)
    deadline_at: float | None       # unix ts, aus agent_delegations.deadline_at bzw. Handoff-Budget
    last_tool_result_summary: str   # erste ~120 Zeichen des letzten Tool-Ergebnisses (kein Volltext)
```

`start()`/`set_tool()` bekommen die neuen Felder als optionale Parameter; `runner.py` und
`handoff_receiver.py` übergeben sie, wo bekannt (Parent-Session aus `ctx`/State, falls via `ask_agent`
delegiert; Iteration/Budget aus `RunSettings`).

`last_tool_result_summary`: nach jedem Tool-Call der ersten ~120 Zeichen des Tool-Ergebnisses (reiner
Text, kein JSON-Dump), serverseitig gekürzt — kein Nutzdaten-Leck über 120 Zeichen hinaus.

`snapshot(owner)` bleibt owner-gefiltert (Sicherheits-Grenze unverändert), liefert jetzt die
Zusatzfelder mit.

## 2. API

Bestehender SSE-Stream `/api/agents/activity/stream` liefert die erweiterten Felder mit — keine neue
Route nötig für die Übersicht.

**Neu:** `GET /api/agents/activity/{session_id}/trace` (nur eigene Sessions, 404 sonst) — Live-Tool-Log
für den Drawer: liest `tool_calls` (DB) für die `session_id`, sortiert nach `created_at`, Felder
`tool_name, arguments (gekürzt), result (gekürzt), status, duration_ms, created_at`. Kein SSE nötig,
Polling alle 2s reicht (Tool-Calls sind nicht so hochfrequent wie Activity-Updates); re-nutzt
bestehendes Muster aus `db/tools.py` falls vorhanden, sonst neue schlanke Query.

## 3. Hierarchie

`agent_delegations` hat schon `agent_id` (Auftraggeber) → `target_agent_id`. Für die Baum-Darstellung
reicht: pro `AgentActivity` die `session_id` des Auftraggebers mitschicken (`parent_session_id`). Das
Frontend baut daraus einen Baum (mehrere Wurzeln möglich: jeder Chat-Agent ohne Parent ist eine
Wurzel).

## 4. Frontend — Seite `/office`

Route `office` im Cockpit-Layout (`App.tsx`, bei den anderen Cockpit-Routen), Nav-Eintrag in
`shared/nav-config.ts` Gruppe `overview`, Icon `Building2` (lucide), labelKey `office`.

### 4.1 Darstellung
- Hintergrund: ein generiertes Büro-Bild (`generate_image`, einmalig, `save_prompt` mit
  `style_anchor`), warmes Cartoon/Illustrations-Stil statt Pixel-Look. Mehrere Varianten (Tag/Nacht
  oder Jahreszeit) sind denkbar, Start mit einer Variante.
- Jeder laufende Agent: ein Charakter-Sprite an einem „Schreibtisch“. Charakter-Grafik je
  **Template-Gruppe** (`personal`/`projects`/`specialists`/`modules`/`system` aus den Agenten-Templates)
  einmalig generiert und per `name`-Hash wie heute stabil zugeordnet (Muster `getCharForAgent`,
  ersetzt durch Bild statt Pixel-Array).
- Verbindungslinie vom Spezialisten zu seinem Auftraggeber (aus `parent_session_id`), analog zum
  toten `interacting`-Feature im Pixel-Monitor, hier aber tatsächlich aus echten Daten gespeist.
- Sprechblase zeigt `last_tool_result_summary` statt nur dem Tool-Namen aus einer festen Tabelle.
- Fortschrittsring am Charakter: `iteration / max_iterations` plus Restzeit bis `deadline_at` (Text
  "noch ~Nmin" wenn < 5 Min, sonst nur der Ring).
- Leerer Zustand: Büro ohne Charaktere, kurzer Text „Gerade arbeitet niemand".

### 4.2 Interaktion
- Klick auf einen Charakter öffnet einen Drawer von rechts: Kopf (Agent-Name, Projekt, seit wann
  aktiv, Template), darunter der Live-Tool-Verlauf (Polling auf die neue Trace-Route), neueste Zeile
  oben. Jeder Eintrag: Icon nach Tool-Art, Tool-Name, Kurzfassung von Argumenten/Ergebnis, Dauer,
  Status-Farbe (ok/Fehler).
- Schließen per X oder Esc.

### 4.3 Sound (optional, Schalter, default aus)
- Dezenter Hinweiston bei Status-Wechsel „läuft" → „fertig" bzw. „Fehler" eines verfolgten (d. h. im
  Drawer geöffneten oder im aktuellen Chat sichtbaren) Agenten — kein Ton für jeden x-beliebigen
  Agenten im Hintergrund, sonst nervt es bei vielen gleichzeitig laufenden.
- Musik (optional, Schalter, default aus): eine leise Ambient-Loop (`generate_music`, einmalig
  erzeugt, als Datei ausgeliefert), Lautstärke-Regler, merkt sich den Zustand in `localStorage`.

## 5. Nicht in dieser Spec
- Reparatur des Chat-Pixel-Monitors (`interacting`-Linien) — eigener kleiner Folge-PR.
- Eingreifen in laufende Agenten von der Büro-Seite aus (abbrechen etc.) — nur Beobachtung.
- Historie vergangener (bereits beendeter) Aufträge auf derselben Seite — reine Live-Ansicht, Historie
  gibt es schon in Dashboard/Sessions.

## 6. Etappen
1. Backend: `AgentActivity` erweitern, `runner.py`/`handoff_receiver.py` befüllen die neuen Felder,
   Trace-Route. Tests zuerst (TDD).
2. Frontend: Seite ohne Grafik (einfache Karten/Kreise, Platzhalter-Farben) — Datenfluss und Drawer
   zuerst zum Laufen bringen, Design danach.
3. Grafik: Büro-Hintergrund + Charakter-Sätze generieren, Platzhalter ersetzen.
4. Sound/Musik-Schalter.

## 7. Akzeptanzkriterien
- [ ] Startet ein Spezialist per `ask_agent`, erscheint er im Büro mit Verbindungslinie zum
      Auftraggeber, binnen 2s (SSE-Push).
- [ ] Fortschrittsring zeigt die echte Iteration/Budget aus dem Template, nicht geraten.
- [ ] Klick auf einen Agenten zeigt echte Tool-Calls dieser Session, nicht die eines anderen Agenten
      (Owner-Filter + Session-Filter geprüft).
- [ ] Ohne laufende Agenten: leerer, aber hübscher Zustand, kein Fehler.
- [ ] Nur eigene Agenten sichtbar (Owner-Filter wie bisher in `snapshot()`), kein Daten-Leck anderer
      Nutzer.
