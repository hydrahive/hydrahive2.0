# Gemeinsame Taskpflege: Tasks und Ideen aller Instanzen im eigenen Projekt

**Stand:** 21.11.2026 · **Status:** Entwurf, Entscheidungen Till 21.11. eingearbeitet, bereit für Review
**Baut auf:** `federation-catalog.md` (Etappen 1–3 gemergt: #734, #736, Module #416, #737;
Etappe 4 Backend auf Branch `feat/federation-catalog-e4-backend`)
**Verwandt:** `server-peering.md`, Module `tasks` (`SPEC-HISTORY.md`, `SPEC-PAGINATION.md`)
und `scratchpad` (`SPEC-IDEEN.md`)

## Problem

Till hat Tasks und Ideen für dasselbe Vorhaben auf mehreren Instanzen, z. B. im
Projekt „Hydrahive DEV“ auf dem Entwicklungsserver (.4) und auf `hydrahome` (.2).
Auf .2 gibt es außerdem Projekte, die es auf .4 nicht gibt. In seinen Worten:

> „Ich habe für Hydrahive auf der .4 und auf der .2 Tasks liegen und muss immer suchen,
> wo ich gearbeitet habe und wie weit es ist. Die eine Instanz kennt die Tasks der
> anderen nicht.“

Der Föderations-Katalog (`federation-catalog.md`) sammelt bisher alles **nur auf dem
Hub**. Clients sehen davon nichts, und bearbeiten kann man fremde Einträge nirgends.

## Zielbild

Öffnet Till auf .4 das Projekt „Hydrahive DEV“, sieht er in den Tasks und Ideen auch
die Einträge von .2, vom Hub und von jeder anderen gekoppelten Instanz, jeweils mit
Stand und erkennbarer Herkunft. Er kann sie dort bearbeiten. Auf .2 und auf dem Hub
ist es genauso.

## Entscheidungen (Till, 21.11.2026 abends)

1. **Fremde Tasks und Ideen dürfen bearbeitet werden.** Die Änderung geht an die
   Ursprungs-Instanz, die bleibt Besitzer.
2. **Projekt-Zuordnung über den gleichen Projektnamen**, im Cockpit korrigierbar.
3. **Ideen gleich mit**, nicht nur Tasks.

Damit entfällt das Nicht-Ziel „Gesamtkatalog auf den Clients“ aus
`federation-catalog.md`. Das Nicht-Ziel „Bearbeiten über Server“ wird für Tasks und
Ideen ebenfalls aufgehoben (dort angepasst).

## Grundsätze (unverändert aus dem Katalog)

- **Hub-Modell bleibt.** Clients sind nur mit dem Hub gekoppelt, nicht untereinander.
  Alles zwischen zwei Clients läuft **über den Hub**. Kein Mesh, keine Hub-Ketten.
- **Der Ursprung bleibt Besitzer.** Nur dort steht der Eintrag in der Modultabelle
  (`module_tasks`, `module_scratchpad_ideas`). Andere Instanzen halten nur eine Kopie
  der **Metadaten** (dieselben Felder wie im Katalog) und lesen den Volltext live.
- **Kein Volltext-Sync.** Beschreibung, Ideentext, Anmerkungen und Verlauf werden nie
  automatisch übertragen, sondern beim Öffnen live beim Ursprung abgefragt.
- **Gleicher Nutzername = gleiche Person** (Entscheidung 21.11.). `till` auf .4 sieht
  die Einträge von `till` auf .2 und auf dem Hub, sonst niemand.
- **Was der Ursprung ausschließt, verlässt ihn nie.** Nicht ausgewählte Nutzer und
  ausgeschlossene Projekte (`federation_catalog_users`,
  `federation_catalog_excluded_projects`) gelten weiter für Push, Nachladen, Verteilen
  und Bearbeiten.
- **Opt-in, Standard aus.** Ohne die neuen Schalter ändert sich am bestehenden
  Katalog nichts.
- **Bestehende Protokollbausteine wiederverwenden:** signierter Kanal, `seq` je
  Partner, `msg_id`-Replay-Schutz, signierte Antwort mit `in_reply_to`
  (`new_catalog_item` aus Etappe 4), Tailnet-Sperre unter `/api/peering/`.

## Schalter (neu)

Je Instanz, in Föderation → Katalog (Admin):

| Schalter | Feld | Wirkung |
|---|---|---|
| **„Gemeinsame Taskpflege“** | `federation_catalog_settings.shared` | Eigene (synchronisierte) Einträge dürfen an die anderen Instanzen weitergegeben werden **und** diese Instanz zeigt fremde Einträge in ihren Projekten. Beide Richtungen in einem Schalter. |
| **„Bearbeiten durch andere Instanzen erlauben“** | `federation_catalog_settings.remote_edits` | Eigene Einträge dürfen von anderen Instanzen geändert werden (nur mit `shared`). |

Der Client meldet beide Werte in jedem `catalog_push` mit (neue Felder `shared`,
`remote_edits`). Der Hub speichert sie in `federation_catalog_sources`. Auf dem Hub
selbst gelten dieselben Schalter für seine eigenen Einträge **und** dafür, ob er
überhaupt verteilt: Ist `shared` auf dem Hub aus, verteilt er nichts.

Der Hub gibt einen Eintrag mit Ursprung **O** genau dann an Client **C**, wenn alle
Bedingungen gelten:

1. Hub: `shared = 1`.
2. O ist der Hub selbst, oder O hat `catalog_accept = 1` am Hub und meldet `shared`.
3. C hat `catalog_accept = 1` am Hub, ist `active` und meldet `shared`.
4. `owner` steht in der Nutzerliste, die C beim Abholen mitschickt (siehe Verteilung).
5. C ≠ O. Eigene Einträge bekommt ein Client nie zurück.

Für Einträge des Hubs gelten zusätzlich die Nutzerauswahl und die ausgeschlossenen
Projekte **des Hubs** (dieselben Tabellen wie auf einem Client).

## Verteilung Hub → Clients

### Warum Abholen mit Kopie statt Live-Abfrage

Die Projekt-Listen der Module fragen alle 5 s neu (`useTasks`, `pollMs = 5000`). Eine
Live-Abfrage beim Hub bei jedem Neuladen wäre unnötige Last und zeigte bei
abgeschaltetem Hub gar nichts mehr. Deshalb hält jeder Client eine **Kopie der
Metadaten** (`federation_catalog_mirror`) und holt Änderungen beim Hub ab. Die Kopie
ist klein, denn Metadaten sind dieselben Felder wie im Katalog (Hunderte bis wenige
Tausend Zeilen). Ist der Hub offline, zeigt der Client den letzten Stand mit Hinweis.

Abgeholt wird vom Client (Richtung Client → Hub wie beim Push). Der Hub braucht so
keine Liste, wann welcher Client erreichbar ist. Damit Änderungen trotzdem schnell
ankommen, stupst der Hub die Clients an (`catalog_notify`, siehe unten).

### Änderungsnummer auf dem Hub

Der Hub vergibt eine fortlaufende Änderungsnummer `rev` (INTEGER, global auf dem Hub):

- `federation_catalog_items.rev` wird bei **jedem** Upsert neu gesetzt (nächster
  Wert aus `federation_catalog_counter`).
- Gelöschte Einträge (Push mit `deleted`, Abgleich, Partner entfernt, Nutzer oder
  Projekt beim Ursprung ausgeschlossen) landen mit eigener `rev` in
  `federation_catalog_deletions` (`rev`, `origin_fp`, `kind`, `item_id`, `owner`,
  `deleted_at`). Diese Zeilen werden nach 7 Tagen entfernt. Ein Client, dessen
  Stand älter ist als die älteste behaltene `rev`, bekommt einen vollen Abgleich.
  Das ist kein dauerhafter Grabstein im Katalog, sondern nur ein kurzes Löschprotokoll
  für die Verteilung.
- **Eigene Einträge des Hubs** werden weiterhin **nicht** in den Katalog kopiert
  (Grundsatz aus `federation-catalog.md`). Sie werden wie bisher über die
  Katalog-Quellen gelesen: `list_changed` mit eigenem Cursor je Art beim Client
  (gleiches Format wie beim Push, nie über Arten hinweg verglichen). Heute tut
  `catalog_changed` auf einer Instanz ohne Hub nichts (`catalog_changes.gate_active`).
  Mit `shared` auf dem Hub merkt es sich die Änderung dort ebenfalls vor. Ein
  Verteil-Schritt prüft je vorgemerktem Eintrag mit `get_full`, ob es ihn noch gibt.
  Fehlt er, schreibt der Hub eine Zeile in `federation_catalog_deletions`. Danach
  stupst er die Clients an. Verpasste Löschungen fängt der stündliche `full`-Abgleich.

Weil `rev` eine ganze Zahl ist, entfällt für Partner-Einträge das Problem der
unterschiedlich genauen Zeitstempel (Tasks sekundengenau, Ideen mikrosekundengenau).

### Nachricht `catalog_pull` (Client → Hub)

`POST https://<hub>/api/peering/catalog/pull`, signiert wie `catalog_push`:

```
{
  "kind": "catalog_pull",
  "msg_id": "<uuid>", "from": "<fingerprint>", "seq": 4712, "issued_at": 1795000000,
  "users": ["till"],                     # = federation_catalog_users des Clients
  "after_rev": 81234,                    # 0 = von vorn
  "local_after": {"task": ["<updated_at>", "<item_id>"] | null, "idea": … },
  "full": false,                         # true = vollständige Schlüsselliste zum Abgleich
  "limit": 500
}
```

- `seq` ist **derselbe Zähler** wie beim Push. Push und Pull laufen unter der
  bestehenden gemeinsamen Sperre streng nacheinander. Der Replay-Schutz `seq` >
  `last_seq` gilt unverändert, es braucht keinen zweiten.
- Prüfreihenfolge wie beim Push (Signatur/Frische → `catalog_accept` → `seq` →
  Rate-Limit), dazu Hub `shared` und C meldet `shared`. Sonst `peer_catalog_not_shared`
  (an den Client, damit er den Grund anzeigt).
- Der Hub merkt sich `users` je Partner (`federation_catalog_sources.pull_users`).
  Das braucht er für Anstupsen und Bearbeiten.

Antwort `200`, signiert (`kind: "catalog_items"`, `in_reply_to` = `msg_id`, Header
`X-HH-Signature`, Mechanik wie `new_catalog_item`):

```
{
  "kind": "catalog_items", "in_reply_to": "<msg_id>", "from": "<hub-fp>", "issued_at": …,
  "items": [ { "origin_fp", "origin_name", "kind", "item_id", "owner", "title", "status",
               "priority", "project_id", "project_name", "created_at", "updated_at" }, … ],
  "deleted": [ {"origin_fp", "kind", "item_id"}, … ],
  "next_rev": 81733, "local_next": {"task": […], "idea": […]}, "more": true,
  "full_keys": [["<origin_fp>", "task", "<item_id>", "<updated_at>"], …] | null,
  "instances": [ {"origin_fp", "origin_name", "last_seen", "stale"} ],
  "ack_seq": 4712
}
```

- `origin_fp` ist der Fingerprint des Ursprungs (beim Hub der eigene), `origin_name`
  der Partnername am Hub. Der Fingerprint ist stabil, der Name kann sich ändern. Der
  Client kann die Angabe nicht selbst prüfen und vertraut hier seinem Hub (wie beim
  Nachladen).
- Höchstens 500 Einträge je Antwort. `more = true` → der Client holt sofort die
  nächste Seite, mit mindestens 2 s Abstand (Rate-Limit 30/min wie beim Push).
- Der Client übernimmt `next_rev`/`local_next` erst, wenn die Seite vollständig in
  `federation_catalog_mirror` geschrieben ist (eine Transaktion). Upsert nur, wenn das
  neue `updated_at` ≥ dem gespeicherten ist (Vergleich nur innerhalb derselben Art).
- `full = true`: Der Hub schickt zusätzlich `full_keys`, die vollständige Liste aller
  für C sichtbaren Schlüssel. Der Client löscht aus der Kopie alles, was fehlt.

### Wann wird abgeholt

- **Nach jedem Timer-Lauf** des bestehenden Katalog-Loops (300 s) unter derselben
  Sperre. Ohne Hub, ohne `enabled` oder ohne `shared` entsteht kein Netzverkehr.
- **Stündlich** mit `full = true` (zusammen mit dem stündlichen Abgleich des Pushs).
- **Auf Anstupsen** durch den Hub, gebündelt 10 s.
- Nach Hub-Wechsel, Ausschalten von `shared` oder Änderung der Nutzerauswahl wird die
  Kopie geleert, der nächste Lauf holt von vorn.

### Anstupsen `catalog_notify` (Hub → Client)

Ändert sich am Hub etwas, das für C sichtbar ist (Upsert, Löschung, eigene Änderung
des Hubs), schickt der Hub gebündelt nach höchstens 10 s
`POST https://<client>/api/peering/catalog/notify` mit
`{"kind": "catalog_notify", "msg_id", "from", "issued_at", "rev"}`. Es enthält
**keine Daten**, nur „es gibt Neues“. Der Client prüft wie bei `catalog_fetch`
(Absender ist sein Hub, `active`, Signatur, Frische, `msg_id` neu, sonst nach außen
`404`) und startet ein Abholen. Geht das Anstupsen verloren, holt der nächste
Timer-Lauf die Änderung. Höchstens ein Anstupsen je Client und 10 s, keine
Wiederholung.

Damit kommt eine Änderung auf .2 in der Regel nach etwa 20 s auf .4 an (10 s Bündelung
beim Push, 10 s beim Anstupsen), spätestens nach einem Timer-Intervall.

### Der Hub als Betrachter

Der Hub braucht keine Kopie: Für seine eigenen Projekt-Listen liest er fremde
Einträge direkt aus `federation_catalog_items`.

## Projektzuordnung

### Regel

Jeder fremde Eintrag trägt `project_id` und `project_name` **des Ursprungs**. Die
betrachtende Instanz ordnet ihn einem eigenen Projekt zu, in dieser Reihenfolge:

1. **Manuelle Zuordnung** in `federation_catalog_project_map` für
   `(username, origin_fp, origin_project_id)`. Ziel ist ein eigenes Projekt oder
   „nicht anzeigen“.
2. **Gleicher Name**: genau ein eigenes Projekt, dessen Name nach Trimmen und ohne
   Unterscheidung von Groß- und Kleinschreibung gleich `project_name` ist **und** in
   dem der Nutzer Mitglied ist (Admins: jedes Projekt).
3. Sonst **nicht zugeordnet**.

Die Zuordnung wird beim Lesen berechnet, nicht gespeichert. Benennt der Ursprung ein
Projekt um, wandert die automatische Zuordnung mit dem neuen Namen. Eine manuelle
Zuordnung hängt an der `origin_project_id` und bleibt.

Einträge ohne Projekt beim Ursprung erscheinen nur in projektübergreifenden Listen
(z. B. Task-Box im Buddy, Ideenliste „alle Projekte“), nie in einem Projekt.

### Projekte, die es nur auf einer Seite gibt

Nicht zugeordnete Einträge (kein gleichnamiges Projekt, Name mehrdeutig, Nutzer kein
Mitglied) tauchen in **keiner** Modul-Projektliste auf. Sie stehen im Cockpit unter
Föderation → Katalog, Bereich **„Nicht zugeordnet“**, gruppiert nach Instanz und
Ursprungsprojekt. Dort kann der Nutzer je Ursprungsprojekt:

- ein eigenes Projekt wählen (manuelle Zuordnung),
- „nicht anzeigen“ wählen (die Einträge bleiben nur im Katalog sichtbar),
- zurück auf „automatisch (gleicher Name)“ stellen.

Projekte selbst werden **nicht** synchronisiert und nie automatisch angelegt.

### Korrektur im Cockpit

Föderation → Katalog → **„Projekt-Zuordnung“**: Tabelle aller Ursprungsprojekte, von
denen der Nutzer Einträge sieht, mit Spalten Instanz · Ursprungsprojekt · Anzahl ·
Zuordnung (Auswahl: automatisch / Projekt … / nicht anzeigen) · Hinweis
(„mehrdeutig“, „kein gleichnamiges Projekt“). Die Zuordnung ist **je Nutzer**: Nur
er sieht diese Einträge, und auch Nutzer ohne Admin-Rechte müssen sie korrigieren
können.

API (Cookie/JWT, jeder angemeldete Nutzer, nur eigene Zeilen):
- `GET /api/federation/catalog/project-map`
- `PUT /api/federation/catalog/project-map` `{origin_fp, origin_project_id, target: "auto" | "hidden" | <project_id>}`
  (Ziel-Projekt muss existieren und der Nutzer Mitglied sein, sonst `404`)

## Anzeige in den Modulen `tasks` und `scratchpad`

### Kern-Schnittstelle (neu, in `ModuleContext`)

Module lesen keine Kerntabellen direkt, der Kern keine Modultabellen. Neu kommen drei
Methoden hinzu, nach demselben Muster wie `catalog_changed` (wirft nie, ohne
`shared`/Hub leer):

```
ctx.catalog_foreign_list(kind, username, project_id | None | "*", statuses, q, limit, offset)
    -> [ForeignItem]          # Kopie (Client) bzw. Katalog (Hub), Zuordnung schon angewandt
ctx.catalog_foreign_get(kind, username, origin_fp, item_id) -> awaitable FullItem | None
ctx.catalog_foreign_edit(kind, username, origin_fp, item_id, changes) -> awaitable EditResult
```

`ForeignItem` = Metadaten + `origin_fp`, `origin_name`, `foreign: true`,
`origin_last_seen`, `stale` (Ursprung länger als zwei Intervalle still oder Hub nicht
erreichbar), `pending_edits` (Anzahl wartender eigener Änderungen).
`project_id` = Ursprungsprojekt, zusätzlich `local_project_id` = Zuordnung.

Die Katalog-Quelle bekommt eine **optionale** fünfte Funktion für den Ursprung:

```
ctx.register_catalog_source(kind, list_changed, list_versions, get_full, query,
                            apply_edit=None)
apply_edit(username, item_id, changes, actor) -> {"result", "fields", "item"}
```

`apply_edit=None` (heutige Module) heißt: Diese Art ist am Ursprung nicht
fernbearbeitbar, Antwort `rejected: not_editable`. Ältere Kerne ohne die neuen
Methoden: Die Module prüfen mit `callable(getattr(ctx, …))` wie bei
`catalog_changed` und zeigen dann einfach keine fremden Einträge.

### Modul-Routen

- `GET /tasks?project_id=…&include_foreign=1` bzw. `GET /ideas?…&include_foreign=1`:
  eigene und fremde Einträge zusammen, fremde mit den Feldern oben. Ohne
  `include_foreign` (ältere Oberflächen) bleibt die Antwort wie heute.
- `GET /tasks/foreign/{origin_fp}/{item_id}` und `GET /ideas/foreign/{origin_fp}/{item_id}`:
  Volltext über den Hub (siehe Nachladen für Clients).
- `PATCH /tasks/foreign/{origin_fp}/{item_id}`, `PATCH /ideas/foreign/{origin_fp}/{item_id}`,
  `POST /ideas/foreign/{origin_fp}/{item_id}/notes`: Bearbeiten (siehe unten).

Eigene und fremde IDs werden nie vermischt: Fremde Einträge haben nur die
`foreign`-Routen. Ein `PATCH /tasks/{id}` mit der ID eines fremden Eintrags ergibt wie
heute `404`.

### Oberfläche

- **TaskPanel** (Reiter „Tasks“ im Projekt) und **IdeasPage**: Fremde Einträge stehen
  in derselben Liste, sortiert wie eigene. Jede fremde Zeile trägt ein Herkunftsabzeichen
  mit dem Instanznamen (z. B. „hydrahome“) und als Tooltip „Stand vom …, zuletzt
  gesehen am …“. Ist der Eintrag `stale`, ist das Abzeichen grau mit „nicht aktuell“.
- Filter-Chip **„Nur diese Instanz / Alle Instanzen“** (Standard: alle). Die Auswahl
  merkt sich die Oberfläche je Modul.
- Die Detailansicht lädt den Volltext live. Ist der Ursprung nicht erreichbar, zeigt
  sie den Snapshot des Hubs mit „Stand vom …“ oder nur die Metadaten mit „<instanz>
  zuletzt gesehen am …“. Ist der Hub selbst nicht erreichbar: Metadaten aus der Kopie
  mit „Hub nicht erreichbar“.
- Wartet eine eigene Änderung, zeigt die Zeile den alten Wert und daneben
  „→ neuer Wert · wartet auf <instanz>“. Die Kopie wird **nicht** vorab geändert. Sie
  ändert sich erst, wenn der Ursprung bestätigt hat.
- Fremde Einträge lassen sich nicht löschen und nicht in ein anderes Projekt
  verschieben (Knöpfe ausgeblendet, Hinweis „gehört zu <instanz>“).
- Neue Tasks und Ideen entstehen immer auf der eigenen Instanz.
- Texte de/en in den Modulen (`texts.de.ts`/`texts.en.ts`).

## Volltext nachladen für Clients: `catalog_read` (Client → Hub → Ursprung)

1. `ctx.catalog_foreign_get(...)` auf Client C schickt signiert
   `POST https://<hub>/api/peering/catalog/read`
   `{"kind": "catalog_read", "msg_id", "from", "seq", "issued_at", "origin_fp", "item_kind", "item_id", "owner"}`.
2. Der Hub prüft die Verteilungsregel (Schalter oben, `owner` ∈ `pull_users` von C,
   Eintrag sichtbar). Sonst nach außen `404`, Grund ins Audit.
3. Der Hub lädt beim Ursprung mit dem **bestehenden** `catalog_fetch` nach (Timeout 8 s,
   damit die Gesamtantwort unter 10 s bleibt) und aktualisiert dabei wie bisher seinen
   Snapshot. Ist O der Hub selbst, liest er lokal über `get_full`.
4. Der Hub antwortet C signiert (`kind: "catalog_item"`, `in_reply_to`) mit Volltext
   oder, wenn der Ursprung offline ist, mit seinem Snapshot und `origin_offline: true`,
   `snapshot_at`, `last_seen`.
5. C zeigt den Text an und **speichert ihn nicht** (kein Snapshot auf Clients).

## Bearbeiten über den Hub an den Ursprung

### Was bearbeitet werden darf

| | Task | Idee |
|---|---|---|
| Titel | ja | ja |
| Status | ja | ja |
| Priorität | ja | – |
| Beschreibung / Ideentext | ja (ganzer Text) | ja (ganzer Text) |
| Notiz/Anmerkung hinzufügen | ja (`note`, wie `TaskUpdate.note`) | ja |
| Anmerkung löschen | – | nein |
| Projekt ändern | nein | nein |
| Löschen | nein | nein |
| Neu anlegen auf fremder Instanz | nein | nein |

Projekt ändern und Löschen bleiben dem Ursprung vorbehalten. Wer einen fremden
Eintrag loswerden will, setzt ihn auf `cancelled` bzw. `dropped`.

### Änderung mit Vergleichswert (Ursprung entscheidet)

Jede Änderung trägt eine `op_id` (UUID) und je Feld den Wert, den der Nutzer gesehen
hat, und den neuen Wert:

```
"changes": {
  "status": {"from": "open", "to": "done"},
  "title":  {"from": "Alt", "to": "Neu"},
  "description": {"from_sha256": "<hash des gesehenen Texts>", "to": "<neuer Text>"},
  "note":   {"add": "Erledigt auf .4"}
}
```

Der Ursprung (`apply_edit`) entscheidet **je Feld**:

- aktueller Wert = `from` (bzw. Hash gleich) → übernehmen,
- aktueller Wert = `to` → nichts zu tun, gilt als übernommen,
- sonst → **Konflikt** für dieses Feld, der Wert beim Ursprung bleibt,
- `note.add` wird immer angehängt (kein Konflikt möglich).

Ergebnis `applied` (alles übernommen), `partial` (mit Liste der Konfliktfelder und
ihren aktuellen Werten) oder `rejected` (Grund: `not_found`, `not_owner`,
`not_shared`, `excluded`, `remote_edits_off`, `not_editable`, `invalid`). Dazu immer
die aktuellen Metadaten des Eintrags.

So hängt die Entscheidung nicht an `updated_at`. Das ist wichtig, weil Tasks nur
sekundengenau speichern und zwei Änderungen in derselben Sekunde nicht
unterscheidbar wären.

Der Ursprung schreibt wie bei einer lokalen Änderung: Tasks sichern die alte Fassung
im Verlauf (`module_tasks_history`), `updated_at` wird gesetzt, `catalog_changed`
löst den normalen Push aus. In den Verlauf bzw. das Audit kommt als Urheber
`<username>@<instanz>` (z. B. `till@hydrahome`). Gleiche Feldprüfungen wie die lokale
API (Status aus der Liste, Titellänge, `MAX_TEXT`).

Die `op_id` merkt sich der Ursprung 30 Tage (`federation_catalog_applied_ops`). Kommt
dieselbe `op_id` noch einmal (Antwort ging verloren, Warteschlange wiederholt),
antwortet er mit dem gespeicherten Ergebnis und ändert nichts.

### Ablauf (Client C bearbeitet Eintrag von Ursprung O)

1. Das Modul ruft `ctx.catalog_foreign_edit(...)`. Der Kern schreibt die Änderung in
   die **Warteschlange** `federation_catalog_outbox` von C (`op_id`, `origin_fp`,
   `kind`, `item_id`, `owner`, `changes`, `created_at`, `state = pending`).
2. Sofort danach (ohne 10-s-Bündelung, der Nutzer wartet) schickt C unter der
   gemeinsamen Sperre signiert `POST https://<hub>/api/peering/catalog/edit`
   `{"kind": "catalog_edit", "msg_id", "from", "seq", "issued_at", "op_id", "origin_fp", "item_kind", "item_id", "owner", "changes"}`.
3. Der Hub prüft Verteilungsregel, `owner` ∈ `pull_users` von C und dass O
   `remote_edits` meldet. Dann leitet er weiter:
   - O ist ein Client: signiert `POST https://<O>/api/peering/catalog/apply`
     `{"kind": "catalog_apply", "msg_id", "from", "issued_at", "op_id", "via": "<C-fp>", "via_name", "item_kind", "item_id", "owner", "changes"}`,
     Timeout 8 s.
   - O ist der Hub: lokal über `apply_edit`.
4. O prüft wie bei `catalog_fetch` (Absender ist sein Hub, `active`, Signatur,
   Frische, `msg_id` neu, `enabled`, `shared`, `remote_edits`, `owner` ausgewählt,
   Projekt nicht ausgeschlossen, Eintrag gehört `owner`). Fehlt etwas: nach außen
   `404`, Grund ins Audit. Sonst `apply_edit` und signierte Antwort
   (`kind: "catalog_applied"`, `in_reply_to`, Ergebnis, Metadaten).
5. Der Hub aktualisiert seine Katalogzeile mit den Metadaten aus der Antwort und
   antwortet C signiert mit demselben Ergebnis.
6. C setzt `state = done` (bzw. `conflict`/`rejected` mit Grund), aktualisiert die
   Kopie und gibt das Ergebnis an das Modul zurück.

Bearbeitet der **Hub** einen Eintrag von O, entfällt Schritt 2/3: Er schreibt in seine
eigene Warteschlange und schickt `catalog_apply` direkt an O.

### Warteschlange, wenn der Ursprung oder der Hub offline ist

- Antwortet der Hub `origin_offline` (O nicht erreichbar, Timeout, gesperrt) oder ist
  der Hub selbst nicht erreichbar, bleibt die Änderung `pending`. Die Oberfläche
  bekommt sofort `queued` und zeigt „wartet auf <instanz>“.
- Die Warteschlange liegt **nur bei der bearbeitenden Instanz**. Der Hub reicht nur
  weiter und speichert nichts. Das hält den Hub zustandslos und passt zum bestehenden
  Muster „keine eigene Wiederholungsschleife, der nächste Timer-Lauf macht es“.
- Wiederholt wird bei **jedem Timer-Lauf** und nach jedem Abholen, bei dem der Hub O
  wieder als nicht `stale` meldet. Reihenfolge: älteste zuerst, je Eintrag streng
  nacheinander. Antwortet O für einen Ursprung `origin_offline`, werden die übrigen
  Änderungen für O in diesem Lauf übersprungen.
- Mehrere wartende Änderungen am selben Eintrag gehen einzeln in Reihenfolge raus.
  Der Vergleichswert der späteren ist der Zielwert der früheren, deshalb passen sie
  zusammen.
- Nach **7 Tagen** ohne Erfolg wird eine Änderung `expired`. Der Nutzer sieht sie in
  der Zeile („nicht übertragen, verworfen“) und im Katalog-Reiter, mit Knopf
  „erneut versuchen“ oder „verwerfen“.
- Löscht oder schließt der Ursprung den Eintrag inzwischen aus, kommt `rejected`.
  Verschwindet der Eintrag aus der Kopie (Abgleich), werden seine wartenden
  Änderungen `rejected: not_found`.

### Konflikte

Der Ursprung gewinnt immer. Konfliktfelder übernimmt die Kopie mit dem Wert des
Ursprungs. Die Oberfläche zeigt einmalig: „Auf <instanz> inzwischen geändert: Status ist
jetzt ‚erledigt‘. Deine Änderung wurde nicht übernommen.“ mit Knopf „Trotzdem
setzen“. Der schickt eine neue Änderung mit dem aktuellen Wert als `from`. Konflikte
bleiben 7 Tage in der Warteschlange sichtbar, dann werden sie entfernt.

Bearbeiten zwei Instanzen denselben Eintrag gleichzeitig, setzt sich die zuerst beim
Ursprung angekommene Änderung durch, die zweite bekommt für dieselben Felder einen
Konflikt.

## Agenten-Werkzeuge `task_*` und `idea_*`

Problem 2 aus `federation-catalog.md` („Agenten legen Tasks doppelt an“) löst sich nur,
wenn auch Agenten fremde Einträge sehen. Vorschlag:

- **`task_list` / `idea_list`** zeigen fremde Einträge im Projekt mit an
  (Kennzeichen `@<instanz>` in der Zeile, z. B. `a1b2c3d4 @hydrahome [open] Titel`).
  Neuer Parameter `instances`: `"all"` (Standard, wenn `shared` an ist) oder
  `"local"`. Gleiche Projekt-Zuordnung wie in der Oberfläche
  (`ctx.project_id` → zugeordnete fremde Einträge).
- **`task_read` / `idea_read`** lösen auch fremde Kurz-IDs auf. Passt eine Kurz-ID auf
  einen eigenen und einen fremden Eintrag, kommt die bestehende Mehrdeutigkeitsmeldung
  von `_ids.resolve` mit beiden Treffern. Volltext über `catalog_read`.
- **`task_write` / `idea_write`** auf einen fremden Eintrag: dieselben Felder und
  derselbe Weg wie in der Oberfläche (Vergleichswert = der Stand, den das Werkzeug
  gerade aus der Kopie liest). Ergebnis als Text: „übernommen“, „wartet auf
  <instanz>“ oder „Konflikt: …“. Neue Einträge legen Werkzeuge immer lokal an.
- **`task_delete`** auf einen fremden Eintrag: abgelehnt mit
  `foreign_delete_not_allowed` und Hinweis auf `cancelled`.

Ob Agenten fremde Einträge **ändern** dürfen oder nur sehen, ist offene Frage 1.

## Datenmodell (neue Kern-Migration)

Nächste freie Nummer bei Umsetzung gegen main und offene PRs prüfen (Stand 21.11.:
`063_federation_catalog_snapshot_stale.sql` ist die letzte, also voraussichtlich
`064_federation_shared.sql`). Gleiche Regeln wie `062`: erst alle
`CREATE … IF NOT EXISTS`, `ALTER TABLE` ans Ende, alles in einer Transaktion.

Auf jeder Instanz:
- `federation_catalog_settings` + `shared`, `remote_edits` (INTEGER, Standard 0),
  `pull_rev` (INTEGER, Standard 0), `pull_local_cursor` (JSON-Text, je Art),
  `last_pull_at`, `last_pull_error`, `last_full_pull_at`
- `federation_catalog_project_map`: `username`, `origin_fp`, `origin_project_id`
  (PK aus allen drei), `target` (`hidden` oder lokale `project_id`), `updated_at`
- `federation_catalog_outbox`: `op_id` (PK), `username`, `origin_fp`, `kind`,
  `item_id`, `changes` (JSON), `state` (`pending`/`done`/`conflict`/`rejected`/`expired`),
  `result` (JSON), `attempts`, `created_at`, `last_try_at`; Index `(state, created_at)`
- `federation_catalog_applied_ops` (Ursprung): `op_id` (PK), `result` (JSON),
  `applied_at`; Einträge älter als 30 Tage werden entfernt

Nur auf Clients genutzt:
- `federation_catalog_mirror`: `origin_fp`, `kind`, `item_id` (PK), `origin_name`,
  `owner`, `title`, `status`, `priority`, `project_id`, `project_name`, `created_at`,
  `updated_at`, `received_at`; Indizes `(owner, project_name)`, `(owner, status)`

Nur auf dem Hub genutzt:
- `federation_catalog_items` + `rev` (INTEGER), Index `(rev)`
- `federation_catalog_counter` (eine Zeile, `rev`)
- `federation_catalog_deletions`: `rev` (PK), `origin_fp`, `kind`, `item_id`,
  `owner`, `deleted_at`
- `federation_catalog_sources` + `shared`, `remote_edits`, `pull_users` (JSON),
  `last_pull_at`

Die Kopie (`federation_catalog_mirror`) wird **nie** wieder gepusht: Sie liegt im
Kern, nicht in den Modultabellen, und die Katalog-Quellen lesen nur Modultabellen.
Eine Schleife „fremder Eintrag kommt als eigener zurück“ ist damit ausgeschlossen.

## Datenschutz und Sicherheit

Alles aus `federation-catalog.md` §Sicherheit gilt weiter. Zusätzlich:

- **Neue Pfade** `/api/peering/catalog/{pull,read,edit,apply,notify}` liegen unter
  der bestehenden Tailnet-Sperre `location /api/peering/`. Ein Test sichert das ab.
- **Ausgeschlossene Projekte und nicht ausgewählte Nutzer** verlassen den Ursprung
  weder beim Push noch beim Nachladen noch beim Bearbeiten. `catalog_apply` auf einen
  solchen Eintrag ergibt nach außen `404`. Schließt der Ursprung später etwas aus,
  verschwindet es per Abgleich vom Hub, landet im Löschprotokoll und verschwindet so
  auch aus allen Kopien.
- **Nur gleicher Nutzername**: In Modul-Listen sieht ein Nutzer nur fremde Einträge
  mit `owner` = eigener Name, auch Admins (wie bei den eigenen Tasks und Ideen). Im
  Katalog-Reiter sehen Admins alles, was die Instanz bekommt.
- **Vertrauen in den Hub**: Ein Client nimmt Kopie, Volltext und Ergebnisse nur von
  seinem Hub an (signiert, `in_reply_to`). Herkunftsangaben (`origin_fp`, `via`)
  stammen vom Hub. Ein Client kann keinen anderen Client direkt ansprechen.
- **Nutzerliste beim Abholen**: Der Hub liefert nur für `users`, die der Client
  meldet. Ein Admin von C kann damit Einträge eines gleichnamigen Nutzers abholen.
  Das folgt aus der Entscheidung „gleicher Nutzername reicht“. Schutz ist das Opt-in
  auf allen Seiten (`shared`, `catalog_accept`).
- **Bearbeiten ist doppelt geschützt**: Ursprung erlaubt es ausdrücklich
  (`remote_edits`, Standard aus) und prüft jede Änderung selbst. Kein Löschen, kein
  Projektwechsel, Vergleichswert je Feld, Verlauf bei Tasks, `op_id` gegen doppelte
  Ausführung.
- **Rate-Limit**: `catalog_pull` zählt zum bestehenden Zähler (30/min).
  `catalog_read` 60/min wie `catalog_fetch`. `catalog_edit`/`catalog_apply` 60/min je
  Partner (eigener Zähler). `catalog_notify` höchstens eines je 10 s.
- **Audit** (`errors_log`, Quelle `federation.catalog`): jede Ablehnung mit Grund,
  jedes Abholen gezählt (Partner, Anzahl), jedes Nachladen und jede Änderung mit
  Partner, Art, Kurz-ID, Nutzer, `via`, Ergebnis, **ohne Inhalt**.
- **Partner sperren/entfernen**: Sperren beendet Abholen, Nachladen und Bearbeiten
  sofort. Entfernen am Hub löscht wie bisher dessen Katalogzeilen. Die Löschungen
  gehen ins Löschprotokoll, die Einträge verschwinden aus allen Kopien. Auf dem
  Client lassen Sperren oder Entfernen des Hubs die Kopie stehen, angezeigt als „Hub
  nicht erreichbar“. „Gemeinsame Taskpflege“ aus oder Hub-Wechsel leert sie.

## API (Cockpit)

- `GET/PUT /api/federation/catalog/settings` + `shared`, `remote_edits` (Admin) und
  Status `last_pull_at`, `last_pull_error`, Anzahl wartender Änderungen
- `GET /api/federation/catalog` (aus Etappe 4) gibt es nun **auch auf Clients**: Dort
  liest es die Kopie und die eigenen Einträge. Filter und Sichtbarkeit wie auf dem
  Hub, zusätzlich Filter `assignment=unassigned`.
- `GET /api/federation/catalog/{origin}/{kind}/{item_id}` auf Clients über `catalog_read`
- `GET/PUT /api/federation/catalog/project-map` (siehe Projektzuordnung)
- `GET /api/federation/catalog/outbox` (eigene wartende, fehlgeschlagene, abgelaufene
  Änderungen), `POST …/outbox/{op_id}/retry`, `DELETE …/outbox/{op_id}`

Signiert, nur Tailnet: `POST /api/peering/catalog/pull`, `…/read`, `…/edit` (Client →
Hub), `…/apply`, `…/notify` (Hub → Client).

## Oberfläche Cockpit

Föderation → **Katalog** (bisher nur Hub) gibt es auf jeder Instanz:
- Liste wie auf dem Hub (Etappe 4), auf Clients aus der Kopie. Einträge sind über die
  Detailansicht bearbeitbar (dieselben Felder wie in den Modulen).
- Bereiche **„Nicht zugeordnet“**, **„Projekt-Zuordnung“** und **„Wartende
  Änderungen“**.
- Im Abschnitt „Katalog-Sync“: Schalter „Gemeinsame Taskpflege“ und „Bearbeiten durch
  andere Instanzen erlauben“, Status „zuletzt abgeholt“.

Hilfe in `help/{de,en}/federation.md` ergänzen.

## Akzeptanzkriterien

G1. Ohne `shared` auf Hub, Ursprung **oder** Betrachter erscheint kein fremder Eintrag
    in Modul-Listen, und `catalog_pull` liefert nichts (`peer_catalog_not_shared`).
    Ohne Hub oder mit Katalog aus entsteht kein Netzverkehr.
G2. Mit allen Schaltern an: Ein neuer Task auf .2 im Projekt „Hydrahive DEV“
    erscheint auf .4 im Reiter „Tasks“ desselben Projekts mit Abzeichen „hydrahome“,
    in der Regel nach ≤ 30 s, spätestens nach einem Timer-Intervall. Genauso
    umgekehrt und für Einträge des Hubs.
G3. Ideen ebenso, inkl. Status und Projektfilter in der Ideenliste.
G4. Ein auf .2 gelöschter oder ausgeschlossener Eintrag verschwindet auf .4 nach dem
    nächsten Abholen bzw. spätestens beim stündlichen Abgleich.
G5. Ein Projekt, das es nur auf .2 gibt, erscheint auf .4 unter „Nicht zugeordnet“
    und in keiner Projektliste. Nach manueller Zuordnung zu einem Projekt auf .4
    erscheinen seine Einträge dort. „Nicht anzeigen“ blendet sie aus den Projektlisten
    aus. Zwei gleichnamige Projekte auf .4 → keine automatische Zuordnung, Hinweis
    „mehrdeutig“.
G6. Status eines fremden Tasks auf .4 ändern, .2 online: übernommen, auf .2 steht der
    neue Status mit Verlauf und Urheber `till@<.4>`, auf .4 aktualisiert sich die Zeile.
G7. Dasselbe mit .2 offline: Zeile zeigt „wartet auf hydrahome“. Nach Wiederkehr von
    .2 wird die Änderung beim nächsten Timer-Lauf übertragen, ohne Zutun.
G8. Konflikt: Auf .2 wird der Status geändert, während auf .4 eine Änderung desselben
    Felds wartet → .2 behält seinen Wert, .4 zeigt den Konflikt und übernimmt den
    Wert von .2. Andere Felder derselben Änderung werden übernommen.
G9. Dieselbe `op_id` zweimal → nur eine Änderung beim Ursprung.
G10. Ohne `remote_edits` beim Ursprung oder für ein ausgeschlossenes Projekt →
     `rejected`, beim Ursprung keine Änderung, Grund im Audit, nach außen `404`.
G11. Fremde Einträge lassen sich weder löschen noch in ein anderes Projekt
     verschieben (Oberfläche, Route, Werkzeug).
G12. Nutzer `anna` auf .4 sieht die Einträge von `till@hydrahome` nirgends, auch
     nicht als Admin in Modul-Listen. Im Katalog-Reiter sieht ein Admin sie.
G13. Gefälschte Signatur, alte `seq`, wiederholte `msg_id`, `catalog_apply` oder
     `catalog_notify` von einem Partner, der nicht Hub ist → abgelehnt (nach außen
     `404` bzw. Fehlercode), Grund im Audit. Neue Pfade von außerhalb des Tailnets → 403.
G14. Detailansicht eines fremden Eintrags auf .4 lädt den Volltext live. .2 offline →
     Snapshot des Hubs mit „Stand vom …“ oder Metadaten mit „zuletzt gesehen am …“;
     Hub offline → Metadaten aus der Kopie mit „Hub nicht erreichbar“. Auf .4 wird
     kein Volltext gespeichert.
G15. Agenten-Werkzeuge: `task_list` im Projekt zeigt fremde Einträge mit `@instanz`,
     `instances="local"` blendet sie aus. `task_read` liest einen fremden Eintrag.
     `task_write`/`task_delete` verhalten sich nach der Entscheidung zu Frage 1.
G16. Regression: alle Akzeptanzkriterien 1–13 aus `federation-catalog.md` bleiben
     erfüllt. Module mit älterem Kern und älteres Modul mit neuem Kern laufen ohne
     Fehler (keine fremden Einträge, sonst unverändert).

## Etappen

Voraussetzung: Etappe 4 des Katalogs (Backend und Oberfläche) ist gemergt. Gebraucht
werden daraus `new_catalog_item` (signierte Antwort), `catalog_fetch`, der Reiter
„Katalog“ und `GET /api/federation/catalog` mit `owners`.

1. **G2 Verteilung (Kern)**: Migration, `rev` + Löschprotokoll auf dem Hub,
   `shared`/`remote_edits` in Einstellungen und Push, `catalog_pull` mit signierter
   Antwort, `catalog_notify`, Kopie auf dem Client, Katalog-Reiter auf Clients (nur
   lesen). AK G1, G4, G13 (Pull/Notify), G16.
2. **G3 Anzeige (Kern + Module)**: Projekt-Zuordnung (Tabelle, API, Bereiche „Nicht
   zugeordnet“/„Projekt-Zuordnung“), `ctx.catalog_foreign_list` und
   `ctx.catalog_foreign_get` mit `catalog_read`; Modul-PR `tasks`/`scratchpad`:
   `include_foreign`, `foreign`-Leseroute, Abzeichen, Filter-Chip, Detailansicht.
   AK G2, G3, G5, G12, G14.
3. **G4 Bearbeiten (Kern + Module)**: Warteschlange, `catalog_edit`/`catalog_apply`
   mit signierten Antworten, `apply_edit` in den Modulen mit Vergleichswerten und
   `op_id`, Verlauf mit Urheber, Oberfläche „wartet auf …“/Konflikt, Bereich
   „Wartende Änderungen“. Wegen des neuen Schreibzugriffs mit Security-Review.
   AK G6–G11, G13 (Edit/Apply).
4. **G5 Agenten-Werkzeuge (Module)**: `task_*`/`idea_*` nach der Entscheidung zu
   Frage 1. AK G15.
5. **G6 Live-Abnahme** .4 ↔ `hydrahive-vps` ↔ `hydrahome` (.2), alle AK G1–G16 mit Till.
   Dafür muss auch .2 als Client am Hub hängen.

Je Etappe ein eigener PR mit grüner CI und Review durch `hydrahive-reviewer`,
Module mit angehobener Version und Test „alter Kern ohne Methode“.

## Nicht-Ziele

- **Projekte synchronisieren oder automatisch anlegen.** Zugeordnet wird nur.
- **Fremde Einträge löschen, in ein anderes Projekt verschieben oder auf fremden
  Instanzen neu anlegen.**
- **Volltext, Anmerkungen oder Verlauf kopieren.** Clients speichern keinen Volltext.
- **Direkte Verbindung zwischen Clients**, mehrere Hubs, Hub-Ketten.
- **Andere Datenarten** (Boards, Tickets, Notizbuch, Memory, Datamining).
- **Abweichende Nutzernamen zuordnen** (till ≠ tschmidt). Gleicher Name reicht.

## Offene Fragen an Till

1. **Agenten und fremde Einträge:** Sollen Agenten fremde Tasks und Ideen nur
   **sehen** oder auch **ändern** dürfen (Status setzen, Notiz anhängen)? Vorschlag:
   sehen ja (gegen Doppelanlage), ändern ja, aber nur Status und Notiz. Titel und Text
   nur durch Menschen.
2. **Ideentext fernbearbeiten:** Ideen haben keinen Verlauf wie Tasks. Soll der
   Ursprung bei einer Fern-Änderung des Ideentexts die alte Fassung als Anmerkung
   sichern, oder soll der Ideentext aus der Ferne gar nicht änderbar sein?
3. **Gleichnamiges Projekt anlegen:** Soll es unter „Nicht zugeordnet“ einen Knopf
   „Projekt hier anlegen“ geben (legt nur ein leeres lokales Projekt mit dem Namen an)?
4. **Ein Schalter oder zwei:** „Gemeinsame Taskpflege“ teilt und zeigt in einem. Reicht
   das, oder soll eine Instanz nur zeigen, ohne zu teilen (oder umgekehrt)?
5. **Standard-Filter in den Modulen:** Fremde Einträge standardmäßig mit anzeigen
   (Vorschlag) oder erst nach Klick auf „Alle Instanzen“?
6. **Wartezeit für die Warteschlange:** 7 Tage bis „verworfen“ – passt das?
