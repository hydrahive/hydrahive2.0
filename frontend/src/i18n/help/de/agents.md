# Agenten

## Was ist das?

Ein Agent ist eine **Konfiguration** — keine laufende Instanz. Er besteht aus: Name, Typ, LLM-Modell, den Bereichen, die er nutzen darf, MCP-Server-Liste, System-Prompt und Memory. Der Agent wird "lebendig" wenn du eine Session mit ihm startest — dann liest der Runner seine Konfig und führt den Tool-Loop aus.

HydraHive2 kennt drei Agent-Typen:

- **Master** — eine Instanz pro User, automatisch beim ersten Login angelegt. Hat alle Tools, kein eingeschränkter Workspace, ist dein persönlicher Assistent.
- **Project** — pro Projekt einer, wird automatisch erstellt wenn du ein Projekt anlegst. Workspace ist auf den Projekt-Ordner beschränkt.
- **Specialist** — frei konfigurierbar für spezifische Domänen (Code-Review, Schreiben, Recherche, …). Was er darf, stellst du im Reiter **Was darf der Agent?** ein.

## Was kann ich hier tun?

- **Neuen Agent anlegen** mit Typ-Auswahl, Modell, Tools
- **Bestehende Agents bearbeiten** — Modell, Temperatur, Max-Tokens, **Was darf der Agent?**, MCP-Server, System-Prompt
- **Aktivieren / Deaktivieren** über Status-Dropdown im Header
- **Löschen** — entfernt Config + Memory + Workspace
- **Memory einsehen** indirekt über Tool-Calls vom Agent

## Was darf der Agent?

Der Reiter **Was darf der Agent?** ersetzt die frühere lange Werkzeug-Liste. Statt einzelner Werkzeuge schaltest du **Bereiche** ein oder aus, jeweils mit einem Satz, was der Agent damit tun kann. Von oben nach unten findest du:

- **Wofür ist dieser Agent da?** (nur für Admins sichtbar) — Schreib in einem Satz, wofür der Agent gebraucht wird (zum Beispiel *Recherchiert im Internet und fasst Ergebnisse zusammen*) und klick auf **Vorschlagen**. Du bekommst passende Bereiche mit einer kurzen Begründung, jeweils mit Häkchen. Mit **Übernehmen** landen die angehakten Bereiche im Entwurf. Der Vorschlag schaltet erst etwas ein, wenn du übernimmst und danach speicherst. Klappt das Vorschlagen nicht, steht dort **Der Vorschlag konnte gerade nicht erstellt werden**. Du kannst die Bereiche dann einfach von Hand einschalten.
- **Werkzeuge bei Bedarf suchen (spart Kosten)** — Der Agent hat dann nur eine kleine Grundauswahl und sucht sich weitere Werkzeuge selbst. Was er darf, ändert sich dadurch nicht. Bei neuen Agenten, die du im Editor anlegst, ist der Schalter an. Bestehende Agenten bleiben, wie sie waren.
- **Die Bereiche** — 28 Schalter in 9 Gruppen (Module können weitere Bereiche mitbringen): **Dateien & Code**, **Internet**, **Organisieren**, **Kreativ**, **Team**, **Nachrichten**, **Zuhause**, **Privates** und **Server**. Zum Beispiel **Dateien lesen**, **Im Internet suchen**, **E-Mails schreiben** oder **Befehle ausführen**.
- **Darf bei Aufträgen zusätzliche Bereiche bekommen** — nur bei Spezialisten und Projekt-Agenten, siehe unten.
- **Expertenansicht** — zugeklappt, für alle, die es genau steuern wollen.

Einige harmlose Werkzeuge erscheinen nicht als Schalter: Skills auflisten und laden, die Hilfe von HydraHive lesen, einen Fehlerbericht vorbereiten, gespeicherte Prompts und die Aufgabenliste der Sitzung. Sie werden in der **Expertenansicht** einzeln vergeben. Ist **Werkzeuge bei Bedarf suchen** an, hat der Agent zusätzlich immer die Werkzeug- und Skill-Suche.

### Markierungen an den Bereichen

Manche Bereiche tragen ein Zeichen. Fährst du mit der Maus darüber, erscheint die Erklärung:

- ⚠️ **Schwer rückgängig zu machen oder wirkt außerhalb von HydraHive** — zum Beispiel Dateien überschreiben, Mails senden, Geräte schalten, Befehle ausführen.
- 🔒 **Zeigt private Daten des Besitzers** — zum Beispiel Gedächtnis, E-Mails lesen, Gesundheit, Finanzen.
- 💶 **Jede Nutzung kostet Geld** — zum Beispiel **Im Internet suchen** oder **Bilder, Musik, Video**.

Ein Bereich ohne Zeichen ist harmlos oder leicht rückgängig zu machen.

### An, aus und teilweise

Jeder Schalter steht auf **an**, **aus** oder **teilweise**. Bei **teilweise** ist nur ein Teil des Bereichs eingeschaltet. Dazu steht der Hinweis *Teilweise: nur ein Teil dieses Bereichs ist eingeschaltet. Ein Klick schaltet alles ein.* Kommt ein Teil nur über eine Kategorie der Expertenansicht, steht dort *Ein Teil kommt über eine Kategorie (Expertenansicht).*

Gibt es neue Werkzeuge in einem Bereich, den du schon eingeschaltet hattest (zum Beispiel, weil ein Modul dazukam), erscheint darunter zum Beispiel **1 neues Werkzeug** mit dem Knopf **Übernehmen?**. Erst wenn du übernimmst und speicherst, darf der Agent sie nutzen.

### Wer darf das ändern?

Die Schalter ändern und speichern nur **Admins**. Alle anderen sehen den Reiter, aber mit dem Hinweis **Nur Admins können die Rechte ändern.** Gespeichert wird wie sonst mit **Speichern** oben im Agenten. Bis dahin ist es nur ein Entwurf.

### Helfer: zusätzliche Bereiche bei Aufträgen

Bei Spezialisten und Projekt-Agenten gibt es zusätzlich den Schalter **Darf bei Aufträgen zusätzliche Bereiche bekommen**. Ist er an, darf ein Agent, der diesen Helfer beauftragt, ihm für den Auftrag bestimmte Bereiche mitgeben. Darunter wählst du, welche. Mit **Helfer-Bereiche speichern** wird das gespeichert (unabhängig vom Knopf **Speichern** oben).

- Bereiche, die nie per Auftrag vergeben werden, stehen ausgegraut da mit **wird nie per Auftrag vergeben**. Das ist heute **Andere Agenten beauftragen**. Bei **Helfer anlegen** wird nur ein Teil nie vergeben, der Schalter bleibt bedienbar.
- Das darf nur der **Besitzer** des Agenten oder ein Admin. Sonst steht dort **Den Pool ändern nur der Besitzer des Agenten oder ein Admin.**
- Normale Nutzer können nur Bereiche weitergeben, die ein Admin für sie freigegeben hat. Sonst kommt **Das darfst du nicht freigeben – nur im Rahmen der Besitzer-Freigabe.**
- Steht im Pool etwas, das zu keinem Bereich passt, weist ein Hinweis darauf hin. Diese Einträge bleiben beim Speichern erhalten.

### Expertenansicht

Klappst du die **Expertenansicht** auf, siehst du die Einzelheiten für Fortgeschrittene: einzelne Werkzeuge, angeheftete Werkzeuge, den Freigabe-Pool und MCP. Hier steuerst du genau, was die Schalter oben zusammenfassen. Im Modus **Werkzeuge bei Bedarf suchen** kommen die angehefteten Werkzeuge und Skills dazu. Das sind die, die der Agent immer sofort zur Hand hat.

## Wichtige Begriffe

- **System-Prompt** — die Anweisungen die der Agent als allererstes sieht. Definiert Persönlichkeit und Verhalten.
- **Memory** — JSON-File pro Agent (`agents/<id>/memory.json`). Agent kann via `read_memory`/`write_memory` lesen und schreiben.
- **Workspace** — Dateisystem-Bereich in dem der Agent operiert. Auto-erzeugt unter `data/workspaces/{master|projects|specialists}/<id>/`.
- **Temperature** — 0.0 = deterministisch, 1.0 = kreativ (Default 0.7).
- **Max Tokens** — Output-Limit pro Antwort. Code-Generation braucht 8000+, Konversation 2000–4000.
- **Thinking Budget** — Extended-Thinking-Tokens (nur Sonnet/Opus 4+). 0 = aus.

## Schritt-für-Schritt

### Specialist-Agent für Code-Review anlegen

1. **+ Neu** klicken
2. Typ **Spezialist**, Modell `claude-sonnet-4-6`, Name `Code-Reviewer`
3. **Anlegen** — der Specialist bekommt nur eine kleine Grundauswahl
4. Im Reiter **Was darf der Agent?** die Bereiche **Dateien lesen**, **Gedächtnis** und, wenn er Befehle ausführen soll, **Befehle ausführen** einschalten. Oder oben beschreiben, wofür er da ist, und **Vorschlagen** klicken
5. System-Prompt-Editor: schreibe genau was er tun soll, z.B.:
   *"Du analysierst Code auf Sicherheits-Probleme, Performance-Issues und Code-Smells. Lies erst die Datei, gib dann strukturiertes Feedback in Markdown."*
6. **Speichern** (Änderungen an den Bereichen speichern nur Admins)

### Master-Agent erweitern mit MCP-Server

1. Master-Agent in der Liste klicken
2. **MCP-Server**-Sektion: angelegte Server ankreuzen
3. **Speichern**
4. Im Chat hat der Agent jetzt zusätzlich `mcp__<server>__<tool>`-Tools

### Einschränken, was ein Agent darf

1. Agent öffnen, Reiter **Was darf der Agent?**
2. Nur die Bereiche einschalten, die der Agent braucht. Wenige Bereiche sind besser: der Agent bleibt gezielter und es kostet weniger
3. **Speichern** — der Agent bekommt beim nächsten Lauf nur noch, was zu den eingeschalteten Bereichen gehört

Einzelne Werkzeuge anhaken oder abwählen geht in der **Expertenansicht**.

## Typische Fehler

- **`Modell '...' ist nicht in der LLM-Konfiguration`** — Modell unter LLM-Konfig ergänzen oder ein bekanntes wählen.
- **`Unbekannte Tools`** — passiert nur wenn manuell in der `config.json` gepfuscht wurde.
- **Agent halluziniert was er kann** — System-Prompt klarer formulieren, im Reiter **Was darf der Agent?** weniger Bereiche einschalten.
- **Agent macht Endlosschleife** — Loop-Detection greift nach 3 identischen Calls; passiert oft bei zu kleinen `max_tokens`.

## Tipps

- **System-Prompt ist die wichtigste Schraube**. Spezifischer = besser. Beispiele für gewünschtes Verhalten reinschreiben.
- **Master-Agent nicht zu generisch halten** — auch er profitiert von einem klaren Profil ("Du bist mein persönlicher Programmier-Assistent…").
- **Specialist-Agents im Projekt nutzen** über `ask_agent` (kommt mit AgentLink): Der Projekt-Agent plant und prüft, die Spezialisten arbeiten.
  - Jeder Auftrag braucht ein kurzes Briefing: `goal` (was am Ende erreicht sein soll) und `deliverable` (was zurückkommen soll), dazu wahlweise `known` (was schon bekannt ist) und `files`.
  - Ein Folgeauftrag aus derselben Sitzung an denselben Spezialisten setzt dessen Sitzung fort, der Spezialist kennt den Stand also schon.
  - Spezialisten mit einem Template „auf Abruf“ (z. B. Security) nehmen nur Reviews an: `task_type="review"` plus `on_demand_reason`.
