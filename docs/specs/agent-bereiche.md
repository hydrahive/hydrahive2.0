# Agenten-Rechte als Bereiche – „Was darf dieser Agent?“

Stand: 27.11.2026 · Status: **Entwurf, wartet auf Tills Freigabe** · Vorgänger: `tool-skill-katalog.md` (Weg A, gemergt #781–#788) · Folge-Task: 92b06561

## 1. Absicht und Warum

Till (27.11., beim Blick auf den Reiter „Tools & MCP“ seines Buddys): „Das ist eine Bibel, da wird man ja erschlagen.“ Und: „Was ich da anklicken und suchen muss, mag für eine KI in einer Sekunde klar sein, aber ein menschlicher Nutzer muss sich wie immer durch Tonnen an Infos wühlen, das dauert Stunden.“ Zum Vorschlag: „In der Art wäre es ideal, auch wenn es 20 Schalter werden. Das ist verständlicher und weitaus übersichtlicher.“

**Heute** zeigt der Editor drei Raster mit Tool-Namen untereinander: die Tools des Agenten, 131 anheftbare Tools und 151 Tools für den Freigabe-Pool. Dazu kommen 31 Skills, alle mit Code-Namen wie `ha_render_template` oder `plugin__git-stats__git_files`.

**Kernidee:** Seit dem Katalog sucht sich der Agent seine Werkzeuge selbst. Ein Mensch muss keine Tools mehr auswählen, sondern nur noch entscheiden, **was der Agent darf**, und zwar in Alltagssprache.

## 2. Was der Nutzer sieht

Im Reiter „Was darf der Agent?“ (ersetzt „Tools & MCP“ als Standardansicht) steht von oben nach unten:

1. **Zweck in einem Satz** (optional): „Wofür ist dieser Agent da?“ → Knopf „Vorschlagen“. Die KI schlägt passende Bereiche vor, jeweils mit einer kurzen Begründung. Der Nutzer übernimmt sie oder hakt sie einzeln an. **Es wird nie ohne Bestätigung etwas eingeschaltet.**
2. **Bereichs-Schalter** (≈ 20), gruppiert unter drei Überschriften: *Arbeiten*, *Zuhause & Privates*, *System & Außenwelt*. Jeder Schalter zeigt:
   - einen Namen und einen Satz, was der Agent damit tun kann;
   - eine Markierung: ohne Zeichen = **nur lesen oder harmlos**, ⚠️ = **verändert etwas, schaltet etwas oder wirkt nach außen**, 🔒 = **private Daten**, 💶 = **kostet Geld pro Nutzung**;
   - den Zustand an, aus oder „teilweise“ (siehe 4.3).
3. **„Werkzeuge bei Bedarf suchen (spart Kosten)“**: ein Schalter. Er ersetzt den Auswahlknopf Klassisch/Katalog und ist bei neuen Agenten an.
4. **„Darf Helfern einen Teil seiner Bereiche mitgeben“**: ein Schalter. Er ersetzt den Freigabe-Pool (siehe 4.4).
5. **„Expertenansicht“**, zugeklappt: die heutigen Listen (Tools, angeheftete Tools und Skills, Pool, MCP) für alle, die es genau steuern wollen.

Angeheftete Tools muss niemand mehr pflegen. Das übernimmt die automatische Anheftung (4.5).

## 3. Die Bereiche (Vorschlag, ≈ 22)

Die **Grundausstattung** hat jeder Agent immer, sie erscheint nicht als Schalter: Skills lesen, HydraHive-Hilfe, gespeicherte Prompts, die Aufgabenliste der Sitzung und die Katalog-Werkzeuge.

| Gruppe | Bereich | Ein Satz für den Nutzer | Markierung | Tools (heute) |
|---|---|---|---|---|
| Arbeiten | Dateien lesen | Dateien und PDFs im Projekt lesen | – | file_read, read_document |
| | Dateien ändern | Dateien im Projekt anlegen und ändern | ⚠️ | file_write, file_patch |
| | Code verstehen | Zusammenhänge im Code und die Git-Historie ansehen | – | graph_*, plugin__code-metrics__*, plugin__git-stats__*, plugin__file-search__* |
| | Im Internet suchen | Suchmaschine befragen | – | web_search |
| | Recherche-Berichte | Mehrstufige Web-Recherche mit Quellen | 💶 | research_report |
| | Gedächtnis | Sich Dinge merken und frühere Gespräche durchsuchen | 🔒 | read/write/search_memory, datamining_* |
| | Aufgaben & Ideen | Tasks, Ideen und Notizzettel lesen und pflegen | – | task_*, idea_*, read_scratchpad |
| | Tickets & GitHub | Tickets anlegen und bearbeiten, mit GitHub verknüpfen | ⚠️ | ticket_*, github_project_*, ticket_github_* |
| | Diagramme & Skizzen | Diagramme und Blueprint-Entwürfe erstellen | – | diagramm_*, blueprint_* |
| | Bücher schreiben | Im Storyteller lesen und Vorschläge ablegen | – | storyteller_* |
| | Bilder, Musik, Video | Medien erzeugen, Bilder beschreiben, Audio abtippen | 💶 | generate_*, analyze_image, transcribe_audio, plugin__minimax-creator__* |
| | Atelier | Figuren, Stil und Drehbuch im Atelier vorbereiten | ⚠️ | atelier_* |
| | Andere Agenten beauftragen | Aufgaben an Helfer-Agenten abgeben | ⚠️ | ask_agent |
| | Helfer anlegen | Neue Spezialisten und Skills im Projekt anlegen | ⚠️ | create_specialist, configure_specialist, list_specialists, write_skill, delete_skill |
| Zuhause & Privates | E-Mails lesen | Postfächer durchsuchen und Mails lesen | 🔒 | read_mail, mailbox_accounts/search/read/attachment |
| | E-Mails schreiben | Entwürfe anlegen, Mails markieren, verschieben, senden | ⚠️ 🔒 | send_mail, mailbox_draft/flag/move |
| | Haus ansehen | Zustand von Lampen, Sensoren und Geräten lesen | – | ha_list_entities, ha_get_state, ha_render_template |
| | Haus steuern | Geräte im Haus schalten | ⚠️ | ha_call_service |
| | Gesundheit | Patientenakte und Gesundheitsdaten lesen | 🔒 | query_fhir_data, query_health_data |
| | Finanzen & Krypto | Kurse, Analysen und das eigene Portfolio ansehen | 🔒 | query_crypto_*, query_portfolio |
| | Recht | Rechtsfälle, Normen, Fristen und Briefentwürfe | 🔒 | legal_* |
| | Filme & Musik laden | Medien suchen und herunterladen | ⚠️ | mediacenter_* |
| System & Außenwelt | Befehle auf dem Server | Programme und Befehle direkt ausführen | ⚠️ | shell_exec |
| | Webseiten öffnen | Seiten abrufen und im Browser bedienen | ⚠️ | fetch_url, web_browser, plugin__http-tester__* |
| | Server verwalten | Webmin: Systemstatus und Einstellungen | ⚠️ | webmin_status, webmin_call |
| | Spiele-Server | RoM-Server: Zonen und Accounts verwalten | ⚠️ | rom_* |
| | Sicherheitsforschung | Tor-Quellen und Reverse-Engineering-Fälle | ⚠️ | opentor_*, reverse_* |

Die Liste ist ein Vorschlag. Namen und Schnitt legt Till fest (E3).

## 4. Wie es funktioniert

### 4.1 Wo die Bereiche stehen
- **Kern:** `hydrahive/agents/areas.py` mit `AREAS` (id, Gruppe, Name de/en, Satz de/en, Markierungen, Tools) und `BASE_TOOLS` (Grundausstattung).
- **Module** melden ihre Bereiche in `manifest.json` unter `agent_areas`, entweder als neuen Bereich oder als Zuordnung ihrer Tools zu einem vorhandenen Bereich. Fehlt die Angabe, landet das Tool unter „ohne Bereich“: Es ist nur in der Expertenansicht zu sehen, und Admins sehen es in einer Liste zum Zuordnen.
- **Wächter-Test:** Jedes Kern-Tool liegt in genau einem Bereich oder in der Grundausstattung.

### 4.2 Was gespeichert wird
**Empfehlung (E1):** Gespeichert werden weiter die einzelnen Tool-Namen in `agent.tools`. Ein Schalter schreibt beim Einschalten die Tools seines Bereichs hinein und nimmt sie beim Ausschalten wieder heraus. Die Bereiche sind nur die Sicht darauf.

Warum nicht `bereich:x` speichern und erst im Lauf auflösen? Dann bekäme ein Agent nach einem Modul-Update **still neue Rechte**, sobald ein Modul seinem Bereich ein Tool hinzufügt. Das wäre bei ⚠️-Bereichen gefährlich.

### 4.3 „Teilweise“ und neue Tools
- **Teilweise:** Hat der Agent nur einen Teil der Tools eines Bereichs, steht der Schalter auf „teilweise“. Ein Klick schaltet den ganzen Bereich ein.
- **Neue Tools:** Kommen nach einem Update Tools in einen eingeschalteten Bereich dazu, zeigt der Schalter „2 neue Werkzeuge – übernehmen?“. Ohne Klick passiert nichts.

### 4.4 Helfer (Freigabe-Pool)
Der Schalter „Darf Helfern einen Teil seiner Bereiche mitgeben“ setzt den Pool auf die **weitergebbaren** Bereiche des Agenten, also dieselben `kategorie:x`-Regeln wie heute. Nie weitergebbar bleiben Shell, Außen-Tools, Authoring, `ask_agent`, Plugin- und MCP-Tools (Spec Katalog S2). Die Ansicht dazu zeigt, welche Bereiche mitgegeben werden dürfen und welche nicht, mit Begründung. Feinsteuerung gibt es nur in der Expertenansicht.

### 4.5 Automatisch anheften
Im Modus „Werkzeuge bei Bedarf suchen“ heftet das System beim **Start eines Laufs** die Tools an, die dieser Agent in den letzten 30 Tagen am häufigsten über `run_tool` benutzt hat. Die Daten kommen aus `catalog_events` (#787), höchstens 8 Tools, nur solche aus `effective_tool_names`.
- Mitten im Lauf ändert sich nichts. Damit bleibt die Cache-Regel unangetastet (Memory `till.prompt_cache_heilig`).
- Hand-Anheftungen aus der Expertenansicht bleiben zusätzlich bestehen.

### 4.6 Vorschlag aus dem Zweck-Satz
- **Route:** `POST /api/agents/{id}/area-suggestion` mit `{purpose}`. Die Antwort ist eine Liste `{area, reason}`.
- **Modell:** das günstige Standardmodell des Besitzers. Eingabe sind nur der Satz und die Bereichsliste (id, Name, Satz), **keine** Agentendaten.
- **Ausgabe:** wird gegen die bekannten Bereich-IDs geprüft, Unbekanntes fliegt raus.
- **Rechte:** nur Besitzer oder Admin, wie das Bearbeiten des Agenten. Der Vorschlag ändert nichts, erst „Übernehmen“ speichert.

### 4.7 Admin-Seiten (aus Task 92b06561) in derselben Sprache
- **Besitzer-Freigabe je Nutzer:** Bereichs-Schalter statt Tool-Listen.
- **Projekt-Pool:** dasselbe.
- **„Neue Werkzeuge zuordnen“:** Tools ohne Bereich bekommen einen Bereich. Das ersetzt die Seite „Kategorie-Bestätigungen“: Technisch bleibt es `approve()`, für den Nutzer heißt es „Werkzeug X gehört zu Bereich Y“.
- **Protokoll:** wer wann welchen Bereich für wen freigegeben oder entzogen hat (`access_audit`), in ganzen Sätzen.

## 5. Was sich NICHT ändert
- Rechteprüfung, Shell-Sperre für Projekt-Agenten und Spezialisten, Datamining-Bereich, Besitzer-Freigabe, Projekt-Deckel: alles wie bisher. Bereiche sind nur eine Sicht auf `agent.tools`.
- Die Tool-Liste innerhalb eines Laufs (Cache).
- Agenten, die heute Tool-Listen haben, sehen ihre Schalter sofort richtig (an, aus oder teilweise). Eine Datenmigration gibt es nicht.

## 6. Entscheidungen für Till
- **E1** Gespeichert werden einzelne Tool-Namen, Bereiche sind nur die Sicht darauf (Empfehlung), *oder* `bereich:x` mit Auflösung im Lauf (neue Modul-Tools kommen dann automatisch dazu).
- **E2** „Werkzeuge bei Bedarf suchen“ für neue Agenten standardmäßig an? Empfehlung: ja, denn die Erprobung zeigt −51 % Prompt-Tokens bei gleichen Antworten.
- **E3** Bereichsliste aus Abschnitt 3: Namen und Schnitt so in Ordnung, oder anders gruppieren und zusammenlegen?
- **E4** Bekommt jeder Nutzer den Zweck-Vorschlag oder nur Admins? Empfehlung: jeder, der den Agenten bearbeiten darf. Er kostet etwa einen Cent pro Klick.

## 7. Abnahme (Vorschlag)
- **AB1** `areas.py` mit allen Kern-Tools. Wächter-Test: jedes Kern-Tool liegt in genau einem Bereich oder in der Grundausstattung.
- **AB2** Module können Bereiche oder Zuordnungen per `agent_areas` melden. Tools ohne Bereich stehen in `GET /api/agent-areas` unter `unassigned`.
- **AB3** Editor: Reiter „Was darf der Agent?“ mit Schaltern (an, aus, teilweise), Markierungen, Gruppen, de/en, Expertenansicht zugeklappt. Ein Schalter ändert genau die Tools seines Bereichs, Test mit Gegenprobe.
- **AB4** „Neue Werkzeuge übernehmen?“ erscheint, wenn ein eingeschalteter Bereich Tools hat, die der Agent nicht hat. Ohne Klick ändert sich nichts.
- **AB5** Zweck-Vorschlag: Route nur für Besitzer oder Admin, Ausgabe gefiltert auf bekannte Bereiche, ändert nichts ohne Übernehmen. Tests für fremden Nutzer, unbekannten Bereich in der Modellantwort und Fehler des Modells.
- **AB6** Automatisch anheften beim Laufstart aus `catalog_events`, höchstens 8, nur wirksame Tools, im Lauf unverändert. Test: Schema-Liste ist innerhalb des Laufs gleich.
- **AB7** Helfer-Schalter setzt den Pool auf die weitergebbaren Bereiche. Nicht Weitergebbares wird mit Begründung angezeigt.
- **AB8** Admin-Seiten (Besitzer-Freigabe, Projekt-Pool, neue Werkzeuge zuordnen, Protokoll) in Bereichssprache.
- **AB9** Tests für alles Neue, Frontend-Build grün, CI 6/6.
