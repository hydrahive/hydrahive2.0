# Agenten-Templates – Modellketten, Budgets und Arbeitsweise an einem Ort

Status: **Entwurf zur Freigabe (Till, 14.11.2026)**. Nur Planung, noch kein Code.
Demo der Seite: `_work/demo/llm-templates-demo.html` (Projekt-Workspace, kein Teil des Repos).

Verwandt: `agentlink-runtime-profiles.md` (wird abgelöst), `central-configuration.md`,
`agent-model-picker.md`, `agent-background-delegation.md`. Tasks: `3994f6b1` (Delegation),
`fc0620e2` (Kosten), `e813b45f` (Fallback bei leerer Antwort).

## 1. Problem

Modell, Fallback und Laufzeitgrenzen stehen heute einzeln in jedem Agenten. Module und
Systemrollen legen ihr Modell zusätzlich selbst fest. Das hat vier Folgen:

1. **Wildwuchs.** Auf .4 (14.11.) haben 41 Agenten 9 verschiedene Kombinationen aus Rolle und
   Modell, 7 davon ohne Fallback. Bei den Spezialisten gibt es 8 verschiedene Budget-Kombinationen
   (Iterationen 8–250, Tokens 4.000–200.000, Timeout 540–3.600 s).
2. **Ausfälle ohne Ersatz.** Das Failover (`runner/_failover.py`) wechselt nur bei 401/402/429/529,
   Quota, Rate-Limit, Overload, Billing und abgelaufenem Login. Bei **Timeout, Abbruch im Stream und
   leerer Antwort** wird nicht gewechselt. Im Streaming-Pfad (`runner/_call.py`) wird nach Fehlern erst
   auf den Nicht-Streaming-Pfad gewechselt; erst dort greift die Modellkette.
3. **Wirkungslose Einstellungen.** Bei Delegation gilt das Minimum aus Agent und Auftragsprofil
   (`agentlink/runtime_profiles.py`). Ohne Angabe ist das Profil `standard` = 32 Iterationen,
   16.384 Tokens, 540 s. Ein Spezialist mit 250 Iterationen und 3.600 s bekommt also trotzdem nur
   32 Iterationen und 9 Minuten.
4. **Abgeschnittene Antworten.** `runner/_handoff_reply.py` kürzt jede Spezialisten-Antwort hart auf
   12.000 Zeichen (Anfang ¾, Ende ¼). Liegt das Ergebnis in der Mitte, fehlt es. Die ganze Antwort
   landet zudem im Kontext des Auftraggebers.

Dazu laufen Module und Systemrollen **am Agenten-System vorbei**, ohne Fallback und mit fest
eingetragenen Modellen (siehe 3.2).

Messung 09.10. auf .2 (Task 3994f6b1): ~90 % des Verbrauchs beim Projekt-Agenten, nur 0,8 % seiner
Werkzeugaufrufe sind `ask_agent`, Kontext im Schnitt 306–349k Tokens.

## 2. Ziel

- **Ein Ort** (LLM-Seite, Reiter „Agenten-Templates“) für alle Rollen, vom Buddy bis zur Zahnfee.
- Jedes Template legt fest: **Modellkette** (Primär → Failover → Notfall), **Budget**, **Antwortformat**.
- Alle Agenten, Module und Systemrollen sind **hart** an ein Template gebunden.
- Failover greift auch bei Timeout, Abbruch und leerer Antwort.
- Eine **feste Arbeitsweise** zwischen Buddy, Projekt-Agent und Spezialisten, die den Kontext klein hält.

Nicht Ziel: neue Anbieter, Preis-/Kostenabrechnung, Änderungen am System-Prompt einzelner Agenten.

## 3. Bestand (gelesen 14.11.2026, main 51dfe1db, Server .4)

### 3.1 Agenten mit eigener Config (`$HH_DATA/agents/*/config.json`)

| Typ | Anzahl | Beispiele |
|---|---|---|
| master | 11 | Buddy und Assistant je Nutzer, HydraVR, joshua22, schmied |
| project | 5 | ein Agent je Projekt |
| specialist | 25 | Backend, Frontend, Security, Tester, Auditoren, 8× RoM, Haushaltsbuch, Videoeditor |

Auf .2 waren es am 09.10. 82 Agenten (21 Projekt, 51 Spezialisten, 10 Master).

### 3.2 Modell-Nutzer außerhalb der Agenten-Configs

| Wer | heute | Quelle |
|---|---|---|
| Labor (hydralabor) | fest `claude-haiku-4-5`, `managed_by` | Modul-Backend |
| Recht (legal) | fest `claude-sonnet-4-6` / `get_default("chat")` | Modul-Backend |
| Storyteller (7 Team-Helfer) | fest `claude-sonnet-4-6` | Modul-Backend |
| Vibe | fest `claude-haiku-4-5`, sonst `default_model()` | Modul-Backend |
| Game-Studio, Deep Research | `default_model()` / eigene Läufe | Modul-Backend |
| Atelier, Studio, Telefonie, Haushaltsbuch, Brettspiele | direkte `complete()`/`stream()` | Modul-Backend |
| Hilfe-Assistent | Chat-Standardmodell | `helpdesk/_agent.py` |
| Zahnfee | eigene Datei `zahnfee.json` | `zahnfee/config.py` |
| Kompaktierung | Chat-Standard bzw. Agent-Kette | `compaction/_llm.py` |
| Lehren | `lessons_model` | `llm/_config.py` |
| Gedächtniskarten | Konsolidierung | `cards/consolidate.py` |
| Medien (Bild, Musik, TTS, STT, Video, Embedding) | `media_models.*`, `embed_model` | `llm/_config.py` |

Medien und Embedding bleiben **außerhalb** der Templates (keine Agenten, andere Modellarten). Sie
bleiben im Reiter „Medien“ der LLM-Seite.

## 4. Optionen

**A. Bindung per Verweis (gewählt).** Agent/Modul speichert nur `template: "<id>"`. Modell, Kette und
Budget werden beim Lauf aus dem Template aufgelöst.
+ eine Wahrheit, eine Änderung wirkt sofort überall. − Umbau Runner, Agent-Seite, Migration.

**B. Kopiervorlage.** Template wird beim Anlegen kopiert, Knopf „auf alle anwenden“.
+ wenig Umbau. − Wildwuchs kommt zurück.

**C. Nur nach Agent-Typ.** Drei Templates (master/project/specialist).
+ sehr einfach. − Reviewer, Security, Übersetzer nicht unterscheidbar.

## 5. Entscheidung

**Option A, harte Bindung.** Im Agenten sind Modell, Fallback und Budget nicht mehr einstellbar;
geändert wird nur das Template. Gegen die Risiken einer harten Bindung:

- **Versionen.** Jedes Speichern erzeugt eine neue Version, alte Versionen lassen sich zurückholen.
- **Vorschau.** Vor dem Speichern zeigt die Seite, welche Agenten und Module betroffen sind.
- **Testlauf.** Knopf schickt eine kurze Frage durch jede Stufe der Kette und zeigt, welche antwortet.
- **Ampel.** Jedes Template zeigt, ob alle Modelle der Kette beim Anbieter verfügbar sind.
- **Ausnahme `managed_by`.** Vom Modul verwaltete Agenten bleiben gebunden, aber das Modul wählt das
  Template (nicht das Modell). Die Wächter-Logik in `agents/_managed.py` bleibt.

## 6. Datenmodell

Neue Datei `$HH_CONFIG_DIR/agent_templates.json` (Schreibzugriff nur Admin, atomar mit Sperre wie
`llm.json`).

```json
{
  "version": 1,
  "templates": {
    "projekt-master": {
      "label": "Projekt-Master",
      "group": "projects",
      "revision": 4,
      "chain": ["claude-opus-5-5", "openai-codex/gpt-5.6-terra", "openrouter/minimax/minimax-m3:free"],
      "failover_on": ["auth", "quota", "rate_limit", "overload", "timeout", "stream_abort", "empty"],
      "cooldown_seconds": 300,
      "budget": {
        "max_iterations": 60, "max_tokens": 32768, "timeout_seconds": 1200,
        "reasoning_effort": "high", "compact_threshold_pct": 40, "cache_ttl": "1h",
        "overrun_pct": 20
      },
      "reply": { "summary_max_chars": 2000, "full_report": "file" },
      "updated_at": "…", "updated_by": "till"
    }
  },
  "history": { "projekt-master": [ { "revision": 3, "…": "…" } ] }
}
```

Agent-Config: neues Feld `template` (Pflicht nach der Migration). Die Felder `llm_model`,
`fallback_models`, `max_iterations`, `max_tokens`, `handoff_timeout_seconds`, `reasoning_effort`,
`compact_threshold_pct`, `cache_ttl` werden **nicht mehr gelesen**, sobald `template` gesetzt ist.
Sie bleiben bis zur Aufräum-Etappe in der Datei, damit ein Zurückrollen möglich ist.

Werte im Beispiel sind **Vorschläge**, nicht festgelegt.

### 6.1 Start-Templates (Vorschlag, Till legt die Modelle fest)

| Template | Gruppe | Primär | Failover | Notfall |
|---|---|---|---|---|
| Buddy | persönlich | Sonnet | ? | ? |
| Assistant | persönlich | ? | ? | ? |
| Projekt-Master | Projekte | Opus | gpt-5.6-terra | MiniMax / lokal |
| Reviewer | Spezialisten | Opus | ? | ? |
| Security | Spezialisten | Fable | ? | ? |
| Backend | Spezialisten | Sonnet | ? | ? |
| Frontend | Spezialisten | Sonnet | ? | ? |
| Recherche | Spezialisten | ? | ? | ? |
| Klein & schnell (Übersetzer, Extraktion) | Spezialisten | ? | ? | ? |
| Modul-Schreiber | Module | ? | ? | ? |
| Modul-Schnell | Module | ? | ? | ? |
| Zahnfee | System | ? | ? | ? |
| Kompaktierung | System | ? | ? | ? |
| Lehren & Karten | System | ? | ? | ? |
| Hilfe | System | ? | ? | ? |

Listenpreise laut `llm/_pricing.py` (je 1 Mio. Tokens, Eingabe/Ausgabe): Fable 5 $10/$50,
Opus 5 $5/$25, Sonnet 5 $2/$10. Für Opus 5.5 und Fable 5.1 ist kein Preis hinterlegt.
→ Security mit Fable nur **auf Abruf** (siehe 9), nicht bei jedem Schritt.

Regel für die Kette: jede Stufe möglichst bei einem **anderen Anbieter**, denn bei Konto-Sperre oder
Limit hilft derselbe Anbieter nicht. Die Seite warnt, wenn zwei Stufen beim selben Anbieter liegen.

## 7. Auflösung zur Laufzeit

Neue Kern-Funktion `agents.templates.resolve(agent_or_role) -> ResolvedTemplate`
(Kette, Budget, Antwortformat). Aufrufer:

- `runner/runner.py` statt `agent["llm_model"]` / `agent["fallback_models"]` / Budgetfelder.
- `agentlink/runtime_profiles.effective_budget` → Budget kommt aus dem Template des **Ziel**-Agenten.
  Die Profile `quick/standard/deep` entfallen als Obergrenze. `ask_agent` darf nur noch
  `overrun: true` + Begründung schicken; dann gilt Budget × (1 + `overrun_pct`/100), höchstens bis zu
  den bisherigen Validierungsgrenzen (250 Iterationen, 200.000 Tokens, 3.600 s). Die Begründung wird
  im Delegationsprotokoll gespeichert.
- Kompaktierung, Zahnfee, Lehren, Karten, Hilfe → eigenes System-Template.
- Module → neue Kern-API `llm.client.complete(template="modul-schreiber", …)` bzw.
  `agents.config.create(template=…)`. Unbekanntes Template → Rückfall auf `chat` mit Warnung im Log,
  kein Absturz.

## 8. Failover härten (Etappe 1, unabhängig von Templates)

- `should_failover` bekommt Kategorien: `auth`, `quota`, `rate_limit`, `overload`, `timeout`,
  `stream_abort`, `empty`. Bisherige Muster bleiben.
- **Timeout**: Verbindungs-/Lese-Timeout und „Stream steht“ (heute `_CONNECTION_ERRORS` mit
  Wiederholversuch) → nach den Wiederholversuchen nächste Stufe statt Abbruch.
- **Leere Antwort**: keine Text- und keine Tool-Blöcke → nächste Stufe (Task e813b45f).
- **Streaming-Pfad**: Die Kette gilt auch beim Streaming. Hat der Stream schon Text gesendet, wird nicht
  gewechselt (sonst doppelte Ausgabe); der Lauf endet mit klarer Fehlermeldung.
- **Sperrzeit**: Ein Modell, das gerade mit `quota`/`auth`/`overload` ausgefallen ist, wird für
  `cooldown_seconds` übersprungen (prozessweit, im Speicher). Kein Dauerfeuer auf einen toten Anbieter.
- Jeder Wechsel wird als Ereignis gespeichert (Modell alt → neu, Grund) und in der Sitzung angezeigt.

## 9. Arbeitsweise in der Hierarchie

Fest im Kern, nicht nur im Prompt:

1. **Buddy** nimmt an, klärt und leitet Projektarbeit an den Projekt-Agenten weiter.
2. **Projekt-Agent** plant, verteilt, prüft. Er bekommt die Regel: Lesen über viele Dateien, Logs,
   Testläufe und Umsetzung gehen an Spezialisten.
3. **Briefing-Pflicht** bei `ask_agent`: Felder `goal`, `known` (was schon feststeht), `deliverable`
   (Antwortformat), `files`. Fehlt `goal` oder `deliverable`, lehnt das Werkzeug mit Hinweis ab.
4. **Antwort**: Der Spezialist liefert eine Kurzfassung (höchstens `summary_max_chars`, Aufbau
   *Ergebnis · Belege · Offene Punkte · Datei*). Die Langfassung wird als Datei im Workspace des
   Auftrags abgelegt und nur als Pfad zurückgegeben. Die harte Kürzung in `_handoff_reply.py` entfällt;
   ist die Kurzfassung zu lang, wird der Spezialist einmal zum Kürzen aufgefordert.
5. **Sitzung weiterführen**: Folgeaufträge an denselben Spezialisten im selben Vorgang setzen dessen
   Sitzung fort (Resume existiert), statt alles neu lesen zu lassen.
6. **Security auf Abruf**: Das Security-Template wird nur über einen expliziten Schritt
   („vor Merge prüfen“) oder auf Wunsch gerufen.

Punkte 3–5 werden erst in **einem** Projekt eine Woche gemessen (Tokens je erledigtem Task,
`ask_agent`-Anteil, Ø Kontext, Fehler/Nacharbeit), dann ausgerollt (Task 3994f6b1, Schritt B/C).

## 10. Oberfläche

LLM-Seite, neuer Reiter **„Agenten-Templates“** (siehe Demo):

- links Liste nach Gruppen mit Ampel und Anzahl gebundener Agenten/Module,
- rechts: Arbeitsweise (Übersicht), Modellkette (3 Stufen, Anbieter-Etikett), Wechselgründe,
  Budget inkl. Überschreitung, Antwortformat, Liste der gebundenen Agenten, Vorschau, Testlauf,
  Version/Zurückholen.
- Reiter **„Zuordnung & Abweichungen“**: alle Agenten und Module mit ihrem Template; während der
  Migration auch „noch nicht gebunden“.
- Agent-Editor: statt Modell/Fallback/Budget nur noch ein Template-Auswahlfeld (+ Link zum Template).
- Alle Texte über i18n (de/en), Design nach Cockpit-Vorgaben.

Rechte: Templates ändern nur Admins. Nutzer wählen für eigene Agenten aus den vorhandenen Templates.

## 11. Etappen

| # | Inhalt | Repo | Risiko |
|---|---|---|---|
| 1 | Failover härten (Kap. 8) | Kern | klein, wirkt sofort |
| 2 | Templates im Kern + API + Seite, Standardmodelle → System-Templates | Kern | mittel |
| 3 | Migration der Agenten: Skript schlägt Zuordnung vor, Till bestätigt, Sicherung vorher | Kern + Betrieb | mittel |
| 4 | Budget aus Template statt Profil, Überschreitung, Antwort als Kurzfassung + Datei | Kern | mittel |
| 5 | Module auf Template-Rollen umstellen, je Modul eigener PR und Release | Module | groß (viele Repos) |
| 6 | Arbeitsweise (Kap. 9): Messung in einem Projekt, dann ausrollen | Kern | mittel |
| 7 | Aufräumen: alte Felder aus Agent-Configs entfernen, Profile `quick/standard/deep` löschen | Kern | klein |

Jede Etappe ist einzeln lauffähig. Etappe 1 lohnt sich auch ohne alle weiteren.

## 12. Akzeptanzkriterien

- Fällt das Primärmodell mit 429, Timeout, Stream-Abbruch oder leerer Antwort aus, antwortet die
  nächste Stufe; die Sitzung zeigt den Wechsel. (Test je Kategorie.)
- Eine Änderung am Template wirkt beim nächsten Lauf auf alle gebundenen Agenten, ohne deren Config
  anzufassen.
- Ein Spezialist mit Template-Budget 96 Iterationen bekommt bei Delegation 96, nicht 32.
- Überschreitung nur mit Begründung und höchstens um `overrun_pct`.
- Spezialisten-Antworten werden nicht mehr in der Mitte abgeschnitten; die Langfassung ist als Datei
  erreichbar.
- Kein Modul und keine Systemrolle nennt nach Etappe 5 noch einen festen Modellnamen im Code
  (Prüfung per grep in CI).
- Unbekanntes oder fehlendes Template führt nie zu einem Absturz, sondern zu `chat` + Warnung.
- Zurückholen einer älteren Template-Version stellt den alten Zustand für alle Gebundenen her.

## 13. Offene Fragen

1. Modelle für die mit „?“ markierten Felder in 6.1.
2. Versuchsprojekt für die Arbeitsweise (Kap. 9).
3. Dürfen Nutzer (nicht Admins) eigene Templates anlegen, oder nur Admins?
4. Notfallstufe „lokal“: welches lokale Modell ist auf .2 dauerhaft verfügbar?
