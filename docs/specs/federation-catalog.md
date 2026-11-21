# Föderations-Katalog: Ideen und Tasks über Server hinweg

**Stand:** 21.11.2026 · **Status:** Entscheidungen getroffen (Till 21.11.), bereit für Review
**Hub:** `hydrahive-vps` (100.89.239.63)
**Verwandt:** `server-peering.md` (Grundlage, freigegeben), `instance-identity.md`
(Entwurf, **noch nicht auf main**, nur auf Branch `docs/instance-identity`),
`datamining-access.md`,
Module `tasks` (`SPEC-HISTORY.md`) und `scratchpad` (`SPEC-IDEEN.md`)

## Problem

Till betreibt mehrere HydraHive-Server: `hydrahome` (.2), `hydrahive-vps` und
künftig weitere. Jeder Server hat seine eigenen Ideen (`module_scratchpad_ideas`)
und Tasks (`module_tasks`). Heute gibt es keinen Ort, an dem man sieht, was auf
allen Servern offen ist:

1. Eine Idee, die auf dem VPS notiert wurde, ist von `hydrahome` aus nicht zu finden.
2. Agenten legen Tasks auf dem Server an, auf dem sie gerade laufen. Wer auf einem
   anderen Server arbeitet, sieht sie nicht und legt sie doppelt an.
3. Die Server-Kopplung (`server-peering.md`) kann nur Agenten-Aufträge. Datenabgleich
   steht dort ausdrücklich unter „Nicht-Ziele (vorerst)“.

Diese Spec hebt dieses Nicht-Ziel **nur für Ideen und Tasks** auf, und auch dort nur
für die Metadaten.

## Bewusste Abgrenzung zur Datamining-Entscheidung

`instance-identity.md` legt für **Datamining** fest (Till, 11./12.10.): **nichts
kopieren**, jeder Server behält sein Datamining, Abfrage **live** in beide Richtungen.
Dort heißt es: „Ein Abgleich der Datenbanken wäre zu viel.“

Für **Ideen und Tasks** hat Till ausdrücklich **Sync** gewünscht (alle paar Minuten
und sofort bei einer neuen Aufgabe). Das ist kein Widerspruch, denn die Daten sind
grundverschieden:

| | Datamining | Ideen + Tasks (dieser Katalog) |
|---|---|---|
| Menge | sehr groß, wächst mit jedem Tool-Call | klein (Hunderte bis wenige Tausend Einträge) |
| Inhalt | volle Gesprächsverläufe, teils sensibel | kurze Titel und Status |
| Nutzung | gezielte Suche bei Bedarf | Überblick „was ist überall offen“, Liste und Filter |
| Entscheidung | **live abfragen, nie kopieren** | **Metadaten synchronisieren, Volltext live nachladen** |

Auch hier wird der Volltext (Beschreibung, Anmerkungen) **nicht** kopiert, sondern
wie beim Datamining live beim Ursprung abgefragt. Memory, Datamining, Dateien und
Projekte bleiben weiter ausgeschlossen (siehe Nicht-Ziele).

## Entscheidung: Hub-Modell auf Basis der bestehenden Server-Kopplung

Verworfen:
- **A) Jeder mit jedem (Mesh):** Bei n Servern gibt es n·(n−1) Sync-Beziehungen und
  jeder Server braucht eine Kopie von allen anderen. Für „einen Ort zum Nachsehen“
  ist das zu viel.
- **B) Eigenes Modul `catalog`:** Der Katalog braucht Schlüssel, Partnerliste,
  signierten Kanal, Tailnet-Sperre und Audit. Das alles liegt im Kern unter
  `hydrahive/federation/`. Ein Modul müsste es nachbauen oder Kern-Interna importieren.

Gewählt: **ein Server ist Hub**, und zwar **`hydrahive-vps`** (100.89.239.63,
Entscheidung Till 21.11.). Er ist mit `hydrahome` schon gekoppelt und getestet,
ein neuer vServer wird nicht gebraucht. Die anderen Server sind
**Clients**, also gewöhnliche gekoppelte Partner des Hubs. Kopplung, Kopplungscode,
Fingerprint-Vergleich und Sperren laufen **unverändert** wie in `server-peering.md`.
Neu kommen hinzu:

- beim Client eine Markierung „dieser Partner ist mein Hub“,
- zwei neue Nachrichtenarten auf dem bestehenden signierten Kanal,
- auf dem Hub eine Katalog-Tabelle mit Metadaten.

Der Katalog ist eine **Kern-Erweiterung von Federation** und kein eigenes Modul.
Weil Tasks und Ideen in Modulen liegen, braucht es eine kleine Schnittstelle zwischen
Kern und Modulen (siehe „Katalog-Quellen“).

## Rollen

- **Client** (z. B. `hydrahome`): schickt die Metadaten seiner Ideen und Tasks an
  den Hub und beantwortet Nachlade-Anfragen des Hubs.
- **Hub** (`hydrahive-vps`): sammelt, speichert und
  zeigt den Katalog. Seine **eigenen** Ideen und Tasks zeigt er direkt aus den lokalen
  Tabellen, ohne sie in den Katalog zu kopieren.
- Es gibt **genau einen Hub pro Client**. Ein Server kann Hub für viele Clients sein.
  Ein Hub hat selbst keinen Hub, weil Ketten nicht vorgesehen sind (siehe Nicht-Ziele).

## Katalog-Quellen (Schnittstelle Kern ↔ Module)

Der Kern liest **keine** Modultabellen direkt. Die Module `tasks` und `scratchpad`
melden sich in `register(ctx)` als Katalog-Quelle an. Die Schnittstelle bietet der
Kern über `ModuleContext` an, so wie heute `register_job` und `register_butler_trigger`:

```
ctx.register_catalog_source(
    kind="task" | "idea",
    list_changed(username, after: (updated_at, item_id) | None, limit) -> [Metadaten],
        # sortiert nach (updated_at, item_id); liefert Zeilen mit (updated_at, item_id) > after
    list_versions(username) -> [(item_id, updated_at)],        # für den stündlichen Abgleich
    get_full(username, item_id) -> {Metadaten + description/body (+ Anmerkungen bei Ideen)} | None,
    query(usernames, project, status, q, limit, offset) -> [Metadaten],  # nur auf dem Hub, eigene Einträge
)
```

`updated_at` bleibt ein **undurchsichtiger Wert der jeweiligen Quelle**. Tasks
speichern sekundengenau (`…T10:00:00Z`, `tasks/backend/service.py`), Ideen
mikrosekundengenau (`…T10:00:00.500000Z`, `scratchpad/backend/store.py`). Als
Strings sortieren die beiden Formate nicht richtig gegeneinander
(`"…00.500000Z" < "…00Z"`). Deshalb gibt es **einen Cursor je `kind`** und es wird
nie über Arten hinweg verglichen (siehe Ablauf 2).

Zusätzlich ruft das Modul nach **jedem** erfolgreichen Schreiben, das `updated_at`
setzt oder eine Zeile anlegt oder löscht, `ctx.catalog_changed(kind, username, item_id)` auf. Das ist der Auslöser für den
sofortigen Push (siehe Ablauf). Die Funktion kehrt sofort zurück und wirft nie. Ist
Federation aus oder kein Hub gesetzt, passiert nichts.

Betroffene Stellen (Stand Modul-Repo 21.11.2026): `tasks/backend/service.py`
(`create_task`, `update_task`, `delete_task`), `scratchpad/backend/store.py`
(`create`, `update`, `delete`), `scratchpad/backend/notes.py` (Anmerkung setzt
`updated_at`), `scratchpad/backend/board_link.py`, `scratchpad/backend/task_link.py`
(legt einen Task direkt an und ändert den Ideenstatus) sowie
`tickets/backend/task_link.py` (INSERT in `module_tasks`). `service.py`/`store.py`
haben kein `ctx`. Das Modul hinterlegt deshalb in `register(ctx)` eine Referenz, die
diese Stellen nutzen. Fehlt ein Aufruf, kommt die Änderung trotzdem an, aber erst
mit dem nächsten Timer-Lauf. Ohne die Anmeldung als Quelle erscheint die Datenart
nicht im Katalog.

**Metadaten** sind genau diese Felder:

| Feld | Task (`module_tasks`) | Idee (`module_scratchpad_ideas`) |
|---|---|---|
| `kind` | `task` | `idea` |
| `item_id` | `id` (UUID; Kurz-ID = erste 8 Zeichen, wie `_ids.resolve`) | `id` |
| `owner` | `username` | `username` |
| `title` | `title` (gekürzt auf 300 Zeichen) | `title` (300 Zeichen) |
| `status` | `open` · `in_progress` · `done` · `cancelled` | `new` · `review` · `planned` · `parked` · `done` · `dropped` |
| `priority` | `priority` | (leer) |
| `project_id`, `project_name` | `project_id` + vom Client aufgelöster Projektname | dito |
| `created_at`, `updated_at` | wie in der Tabelle | wie in der Tabelle |

**Nicht** in den Metadaten: `description`/`body`, Anmerkungen, Verlauf (`module_tasks_history`),
`session_id`, `source_kind`/`source_id`, `board_id`. Die Herkunfts-Instanz setzt der
**Hub** aus dem Partner, dessen Signatur er geprüft hat. Der Client kann sie nicht
selbst angeben.

## Datenmodell (neue Migration)

Neue Kern-Migration analog zu `053_federation_peers.sql`, Dateiname
`062_federation_catalog.sql`. Das ist die nächste freie Nummer, geprüft gegen main
`beef4841`, alle Remote-Branches und offenen PRs am 21.11.2026. Vor dem Anlegen noch
einmal gegen main prüfen.

**Reihenfolge in der Datei:** Erst alle `CREATE TABLE/INDEX IF NOT EXISTS`, die beiden
`ALTER TABLE` und den Teil-Index ganz ans Ende. Der Migrations-Runner
(`db/migrations.py`) markiert eine Migration bei „duplicate column name“ als komplett
angewendet. Ein Abbruch nach dem ersten `ALTER` würde sonst die übrigen Tabellen für
immer verhindern. Alternativ werden die `ALTER`s in eine eigene Migration 063 ausgelagert.

### Erweiterung `federation_peers`

```
-- ganz am Ende der Migration
ALTER TABLE federation_peers ADD COLUMN is_hub INTEGER NOT NULL DEFAULT 0;
ALTER TABLE federation_peers ADD COLUMN catalog_accept INTEGER NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS idx_federation_peers_single_hub
    ON federation_peers (is_hub) WHERE is_hub = 1;
```

- `is_hub` (wird **auf dem Client** gesetzt): Dieser Partner ist mein Hub. Der
  Teil-Index lässt höchstens einen Hub zu. Gesetzt werden kann er nur bei
  `status = 'active'`.
- `catalog_accept` (wird **auf dem Hub** gesetzt): Ich nehme Katalog-Daten von diesem
  Partner an. Standard aus. Das ist das Gegenstück zum Recht „Datamining abfragen“ in
  `instance-identity.md` und zu den Agent-Freigaben in `server-peering.md`.

Eine Spalte statt einer eigenen Tabelle, weil die Hub-Eigenschaft genau einen Partner
betrifft und mit ihm gelöscht wird. Der Client sendet nur, wenn der Hub-Partner
`status = 'active'` hat. Ist er gesperrt (`blocked`), ruht der Sync. Ein Server, der
selbst Katalog-Daten annimmt (`catalog_accept = 1` bei irgendeinem Partner), kann
keinen Hub setzen und umgekehrt. Die Einstellungs-Routen lehnen das mit `409` ab.

### Client-Seite

`federation_catalog_settings` (eine Zeile)
- `enabled` (0/1, Standard 0): Opt-in des Admins für diesen Server
- `interval_seconds` (Standard 300, erlaubt 60–3600)
- `seq`: laufende Nummer der letzten gesendeten Nachricht

`federation_catalog_cursors` (je Nutzer und Art)
- `username`, `kind` — Primärschlüssel
- `cursor_updated_at`: `updated_at` des letzten **vollständig bestätigten** Laufs, im
  Format der Quelle; wird nur mit Werten derselben Art verglichen
- `last_push_at`, `last_ok_at`, `last_full_at`, `last_error`

`federation_catalog_users`
- `username`: Nutzer, deren Ideen und Tasks gesynct werden. Standard: **leer**, es
  wird also nichts gesendet, bis der Admin Nutzer auswählt.

`federation_catalog_excluded_projects`
- `project_id`: Projekte, die nie gesendet werden (z. B. Projekte mit Gesundheitsdaten)

### Hub-Seite

`federation_catalog_items`
- `peer_id` (FK `federation_peers` ON DELETE CASCADE), `kind`, `item_id`
  — Primärschlüssel `(peer_id, kind, item_id)`
- `owner`, `title`, `status`, `priority`, `project_id`, `project_name`
- `created_at`, `updated_at` (vom Ursprung), `received_at` (Hub)
- `snapshot_body`, `snapshot_at`: zuletzt live nachgeladener Volltext (siehe Nachladen), sonst leer
- Indizes: `(owner, status)`, `(peer_id, project_name)`, `(updated_at)`;
  Volltextsuche über `title` mit FTS5: `federation_catalog_fts` als
  External-Content-Tabelle (`content='federation_catalog_items'`) mit
  Insert/Update/Delete-Triggern. Die Löschung per `ON DELETE CASCADE` löst die
  Delete-Trigger aus. Eine eigenständige FTS-Tabelle würde beim Entfernen eines
  Partners verwaiste Zeilen behalten.

`federation_catalog_sources`
- `peer_id` (PK, FK `federation_peers` ON DELETE CASCADE), `last_seq`, `interval_seconds`
  (vom Client gemeldet), `last_push_at`, `last_full_at`, `item_count`

Gelöschte Einträge werden auf dem Hub **entfernt**, nicht als Grabstein behalten.

## Ablauf

### 1. Hub koppeln und markieren (einmalig)

1. Client und Hub koppeln sich wie in `server-peering.md`: Kopplungscode, Fingerprint
   vergleichen, bestätigen. Nichts daran ändert sich.
2. **Auf dem Client**: Föderation → Server → Partner → Schalter **„Als Hub für den
   Katalog verwenden“**. `PUT /api/federation/peers/{id}/hub {"is_hub": true}`. Ist
   schon ein anderer Partner Hub, fragt die Oberfläche nach und wechselt dann.
3. **Auf dem Client**: Föderation → Katalog → **„Katalog-Sync aktivieren“**, Nutzer
   auswählen, optional Projekte ausschließen.
   `PUT /api/federation/catalog/settings`.
4. **Auf dem Hub**: Föderation → Server → Partner → Schalter **„Katalog annehmen“**.
   `PUT /api/federation/peers/{id}/catalog {"accept": true}`.

Erst wenn alle drei Schalter an sind, fließen Daten (Opt-in auf beiden Seiten).
Die Reihenfolge von 2–4 ist egal. Bis der Hub annimmt, bekommt der Client
`peer_catalog_not_accepted` und zeigt es im Status an.

### 2. Sync-Trigger

**Timer: alle 300 s (5 min).** Ein eigener Kern-Loop, gestartet in
`api/lifespan.py` nach dem Muster der vorhandenen `run_loop`-Tasks mit Stop-Event
(z. B. `zahnfee_scheduler.run_loop`). `ModuleContext.register_job` gibt es nur für
Module und legt das Intervall fest. Der Loop liest `interval_seconds` dagegen bei
jedem Durchlauf aus den Einstellungen, damit Änderungen ohne Neustart wirken. Erster
Lauf 60 s nach dem Start.

**Cursor-Verfahren (je Nutzer und Art):**
1. Der Lauf startet bei `updated_at >= cursor_updated_at`, also **einschließlich**
   des Cursorwerts. Die zuletzt bestätigte Zeitstufe wird damit jedes Mal noch einmal
   mitgeschickt. Das ist gewollt: Tasks sind nur sekundengenau, und eine zweite
   Änderung in derselben Sekunde ginge mit `>` verloren. Der Upsert auf dem Hub ist
   idempotent, doppelte Einträge schaden nicht.
2. Innerhalb eines Laufs wird nach `(updated_at, item_id)` geblättert (Keyset,
   `list_changed(after=…)`), in Nachrichten zu höchstens 500 Einträgen. So entsteht
   auch bei mehr als 500 Einträgen mit gleichem `updated_at` keine Endlosschleife.
3. Erst wenn **alle** Nachrichten des Laufs bestätigt sind, setzt der Client
   `cursor_updated_at` auf das höchste gesendete `updated_at` dieser Art. Bricht der
   Lauf ab, bleibt der Cursor stehen und der nächste Lauf wiederholt ihn.

Begründung für 5 Minuten:
- Den sofortigen Fall deckt der Event-Push ab. Der Timer ist nur das Sicherheitsnetz
  für verlorene Events, Neustarts und Zeiten, in denen der Hub nicht erreichbar war.
  Kürzer bringt also kaum mehr Aktualität.
- Kosten: Ein leerer Lauf ist ein einzelner signierter POST mit leerer Liste
  (Lebenszeichen, setzt `last_seen`). Bei 10 Clients sind das 2 Anfragen pro Minute
  am Hub, weit unter dem Rate-Limit (30/min pro Partner).
- Es passt zur Nachrichten-Frische `MAX_AGE_SECONDS = 300` in `peer_protocol.py`:
  Der Client meldet sein `interval_seconds` in jedem Push mit. Hat der Hub länger
  als **zwei** Intervalle nichts gehört, markiert er den Client als „nicht aktuell“
  (siehe Oberfläche). Zwei statt eins, damit ein einzelner verspäteter Lauf keinen
  Fehlalarm auslöst.
- Einstellbar ist 60–3600 s. Weniger als 60 s ist nicht sinnvoll, weil der
  Event-Push schneller ist.

**Event-Push: sofort, mit 10 s Bündelung.** `ctx.catalog_changed(...)` merkt den
Eintrag vor und startet einen Push nach höchstens 10 s. Schreibt ein Agent fünf Tasks
hintereinander, geht trotzdem nur eine Nachricht raus. Schlägt der Push fehl, gibt es
**keine** eigene Wiederholungsschleife: Der Cursor bleibt stehen und der nächste
Timer-Lauf schickt alles mit. So entsteht kein Wiederholungssturm, wenn der Hub
offline ist.

**Abgleich: stündlich.** Der Delta-Push sieht Löschungen nicht, weil gelöschte
Zeilen kein `updated_at` mehr haben. Deshalb schickt jeder zwölfte Timer-Lauf (oder
einer, der mehr als 60 min nach `last_full_at` kommt) zusätzlich die vollständige
Liste `(item_id, updated_at)` je Nutzer und Art (`full_versions`). Der Hub entfernt
alles, was dort fehlt. Fehlen ihm Einträge oder ist sein `updated_at` ein anderes,
antwortet er mit `resync: [{username, kind}]`. Der Client setzt für diese Paare den
Cursor zurück und schickt sie im nächsten Lauf vollständig. Damit repariert der
Abgleich auch verpasste Änderungen, nicht nur Löschungen. Eine Löschung, die einen Event-Push auslöst, wird sofort als `deleted`
mitgeschickt. Der stündliche Abgleich fängt nur verpasste Löschungen auf.

**Nutzer- oder Projektauswahl geändert, Hub gewechselt:** Der Cursor wird
zurückgesetzt, der nächste Lauf ist ein voller Abgleich.

### 3. Nachricht `catalog_push` (Client → Hub)

`POST https://<hub>/api/peering/catalog/push`, signiert wie Aufträge
(`X-HH-Peer`, `X-HH-Signature`, Ed25519 über die kanonische JSON-Form):

```
{
  "kind": "catalog_push",
  "msg_id": "<uuid>",
  "from": "<fingerprint>",
  "seq": 4711,
  "interval_seconds": 300,
  "issued_at": 1795000000,
  "items":   [ {Metadaten}, … ],          # höchstens 500 je Nachricht
  "deleted": [ {"kind": "task", "item_id": "…"}, … ],
  "full_versions": { "till": { "task": [["<id>", "<updated_at>"], …], "idea": […] } } | null
}
```

Der Hub prüft in dieser Reihenfolge und lehnt jeweils ohne Details nach außen ab:
1. Absender gekoppelt und `active`, Signatur gültig, `issued_at` frisch
   (`verify_incoming` wie bisher)
2. `catalog_accept = 1` für diesen Partner, sonst `peer_catalog_not_accepted`
3. `seq` > `last_seq` des Partners, sonst `peer_replay`. Damit braucht der
   Replay-Schutz für Katalog-Nachrichten **keine** Zeile in `federation_peer_tasks`,
   die sonst alle 5 Minuten wachsen würde. Die Ablehnung enthält ausnahmsweise
   `last_seq`, damit ein Client nach einem Backup-Restore auf `last_seq + 1` springen
   kann. Das ist unbedenklich, denn der Absender ist zu diesem Zeitpunkt schon als
   gekoppelter Partner mit gültiger Signatur geprüft.
4. Rate-Limit pro Partner (eigener Zähler, 30/min) und Größenlimit (nginx 1 MB,
   höchstens 500 Einträge, Titel ≤ 300 Zeichen)
5. Felder gültig: `kind` ∈ {task, idea}, Status aus der jeweiligen Liste. Ungültige
   Einträge werden einzeln verworfen und gezählt, nicht die ganze Nachricht.

Danach schreibt der Hub per Upsert in `federation_catalog_items`. Eine Zeile wird nur
überschrieben, wenn das neue `updated_at` ≥ dem gespeicherten ist. Ändert sich
`updated_at`, wird `snapshot_body` als veraltet markiert. Antwort `200` mit
`{"ack_seq": 4711, "resync": [] }`. Der Cursor wird erst weitergesetzt, wenn alle
Nachrichten des Laufs bestätigt sind (Ablauf 2). Gehen Nachrichten verloren, kommen sie also
beim nächsten Lauf noch einmal.

Bei mehr als 500 Änderungen schickt der Client mehrere Nachrichten nacheinander mit
steigender `seq`, jede wird einzeln bestätigt.

### 4. Volltext nachladen: `catalog_fetch` (Hub → Ursprung)

1. Ein Nutzer öffnet auf dem Hub einen Katalog-Eintrag:
   `GET /api/federation/catalog/{peer_id}/{kind}/{item_id}`.
2. Der Hub schickt signiert
   `POST https://<client>/api/peering/catalog/fetch`:
   `{"kind": "catalog_fetch", "msg_id", "from", "issued_at", "item_kind", "item_id", "owner"}`.
   Das funktioniert, weil die Kopplung ohnehin gegenseitig ist: Der Client kennt
   den Hub als aktiven Partner.
3. Der Client prüft: Absender ist **sein Hub** (`is_hub = 1`) und `active`, Signatur
   gültig, frisch, Sync `enabled`. `owner` steht in `federation_catalog_users`, das
   Projekt ist nicht ausgeschlossen, und der Eintrag gehört wirklich `owner`. Fehlt
   eine dieser Bedingungen, kommt nach außen **immer `404`** ohne Code und ohne Angabe,
   ob es den Eintrag gibt. Der genaue Grund (`peer_not_hub`, `peer_catalog_disabled`,
   Nutzer/Projekt ausgeschlossen, unbekannt) geht nur ins Audit. Replay-Schutz:
   `msg_id` wird für die Frischezeit (`MAX_AGE_SECONDS`) im Speicher gehalten,
   eine Wiederholung bekommt ebenfalls `404`.
4. Der Client antwortet **synchron** (kein Auftrag im AgentLink, wie die
   Datamining-Abfrage in `instance-identity.md`) mit `get_full(...)`: Metadaten,
   Beschreibung bzw. Ideentext und bei Ideen die Anmerkungen, gekürzt auf
   `MAX_TEXT` (200 000 Zeichen). Die Antwort ist selbst signiert
   (`kind: "catalog_item"`, Header `X-HH-Signature`) und wiederholt die `msg_id` der
   Anfrage (`in_reply_to`). Der Hub prüft Signatur, Frische und dass `in_reply_to`
   seine eigene offene Anfrage ist. `send_signed`
   signiert heute nur die Anfrage, deshalb braucht es hier eine kleine Ergänzung.
5. Der Hub zeigt den Volltext, aktualisiert die Metadaten der Zeile und speichert
   den Text als `snapshot_body` mit `snapshot_at`.

**Ursprung offline** (Timeout 10 s, Netzfehler, gesperrt): Der Hub zeigt die
gespeicherten Metadaten, den letzten `snapshot_body` (falls es einen gibt, mit dem
Hinweis „Stand vom …“ und „veraltet“, wenn sich `updated_at` seither geändert hat)
und **„<instanz> zuletzt gesehen am <federation_peers.last_seen>“**. Einen
Fehlertext als Inhalt gibt es nie.

**Entscheidung Till (21.11.):** Der zuletzt geöffnete Volltext darf als Snapshot
auf dem Hub gespeichert bleiben, damit „Ursprung offline“ etwas anzeigen kann. Der
Snapshot entsteht nur, wenn jemand den Eintrag öffnet. Er wird nie aktiv vom Client
geschickt. Das ist mit dem Grundsatz „Volltext nicht automatisch syncen“ vereinbar.
Löscht der Ursprung den Eintrag oder schließt er Nutzer/Projekt aus, verschwindet
mit der Katalog-Zeile auch der Snapshot (spätestens beim stündlichen Abgleich).

### Änderungen an `peer_protocol.py`

- Neue Konstruktoren `new_catalog_push`, `new_catalog_fetch`, `new_catalog_item`
  nach dem Muster von `new_task`/`new_reply`.
- `verify_incoming` prüft heute fest `task_id`. Es bekommt einen Parameter für das
  ID-Feld (`id_field="task_id"` als Standard, `"msg_id"` für Katalog-Nachrichten).
  Bestehende Aufrufe für `task`/`reply` bleiben unverändert.
- Neue Fehlercodes: `peer_catalog_not_accepted` (nach außen an den Client, damit er
  den Grund anzeigen kann), `peer_not_hub` und `peer_catalog_disabled` (nur im Audit,
  nach außen `404`, siehe Ablauf 4).

## Sicherheit

Grundlage wie in `server-peering.md`, ohne Abschwächung:

- `/api/peering/catalog/*` liegt unter dem bestehenden `location /api/peering/`
  (Installer `60-nginx.sh`, Linux und Mac): nur Tailnet (`100.64.0.0/10` und
  Tailscale-IPv6), `client_max_body_size 1m`, kein Cookie, kein JWT, nur Ed25519.
  Es braucht **keine** neue nginx-Regel. Ein Test sichert ab, dass die neuen Pfade
  unter der Sperre liegen.
- **Opt-in auf beiden Seiten**: Client `enabled` + Nutzerauswahl + `is_hub`, Hub
  `catalog_accept`. Standard überall aus.
- **Wessen Daten sieht man auf dem Hub?** Ein Eintrag mit `owner = till` ist auf dem
  Hub nur für den gleichnamigen Nutzer `till` sichtbar und für Admins.
  **Entscheidung Till (21.11.): gleicher Nutzername reicht** (till@hydrahome =
  till@hydrahive-vps), eine Zuordnungstabelle je Partner gibt es nicht. In
  `instance-identity.md` steht dieselbe Frage für das Datamining noch als offen.
  Sie ist damit für beide Specs gleich beantwortet und sollte dort beim nächsten
  Stand nachgetragen werden.
- **Herkunft nicht fälschbar**: Die Instanz eines Eintrags ist immer der Partner,
  dessen Signatur geprüft wurde. Ein Client kann keine Einträge unter fremdem
  Namen ablegen und keine fremden Einträge überschreiben, weil der Schlüssel
  `peer_id` enthält.
- **Nachladen nur durch den eigenen Hub**: Ein anderer gekoppelter Partner kann
  `catalog_fetch` nicht nutzen (nach außen `404`, im Audit `peer_not_hub`). Damit wird die Server-Kopplung nicht
  zum allgemeinen Lesezugang auf Tasks.
- **Sensible Projekte**: Der Admin kann Projekte ausschließen. Titel und Text aus
  ausgeschlossenen Projekten verlassen den Server weder beim Push noch beim Nachladen.
- **Rate-Limit**: 30 Katalog-Nachrichten pro Minute und Partner (eigener Zähler
  neben dem für Aufträge), `catalog_fetch` 60 pro Minute.
- **Audit** (`errors_log`, Quelle `federation.catalog`): jeder abgelehnte Push und
  Fetch mit Grund. Angenommene Pushes werden nur gezählt (Partner, Anzahl
  Einträge/Löschungen), ohne Titel. Jedes Nachladen mit Partner, Art, Kurz-ID und
  anfragendem Nutzer, ohne Inhalt.
- **Partner sperren oder entfernen**: Sperren beendet Push und Fetch sofort.
  Entfernen löscht per `ON DELETE CASCADE` alle Katalog-Einträge dieses Partners
  auf dem Hub.
- Der private Schlüssel und AgentLink bleiben wie gehabt (`127.0.0.1`, `signing.py`
  pro Server).

## API (Cockpit, Cookie/JWT wie die übrigen `/api/federation/*`-Routen)

Client:
- `PUT /api/federation/peers/{id}/hub` `{is_hub}` (Admin)
- `GET /api/federation/catalog/settings` (Status: aktiv, Hub, letzter Push/Erfolg/Fehler, Anzahl wartender Änderungen)
- `PUT /api/federation/catalog/settings` `{enabled, interval_seconds, users[], excluded_projects[]}` (Admin)
- `POST /api/federation/catalog/sync-now` (Admin; voller Abgleich sofort)

Hub:
- `PUT /api/federation/peers/{id}/catalog` `{accept}` (Admin)
- `GET /api/federation/catalog?instance=&project=&status=&kind=&q=&limit=&offset=`
  (seitenweise; enthält die eigenen lokalen Einträge des Hubs mit dessen Instanznamen.
  Ist „dieser Server“ im Filter, fragt der Hub die eigenen Quellen über `query(...)`
  mit `limit + offset` ab, mischt nach `updated_at` absteigend mit den Katalogzeilen
  und schneidet die Seite aus. Bei den erwarteten Mengen von wenigen Tausend
  Einträgen reicht das, eine gemeinsame Tabelle ist nicht nötig.)
- `GET /api/federation/catalog/{peer_id}/{kind}/{item_id}` (Metadaten + live nachgeladener Volltext oder Snapshot mit Offline-Hinweis)

Signiert, nur Tailnet:
- `POST /api/peering/catalog/push` (Client → Hub)
- `POST /api/peering/catalog/fetch` (Hub → Client)

## Oberfläche

**Föderation** bekommt den Reiter **„Katalog“** (`catalog` in `federationTabs.ts`).
Heute gibt es dort schon `workstations`, `peers` (Server), `clients` und `datamining`.
Der neue Reiter kommt nach „Server“.

**Auf dem Hub**: Liste aller Einträge
- Spalten: Art (Symbol Idee/Task), Kurz-ID, Titel, Status, Projekt, Instanz,
  geändert am
- Filter: Instanz (Mehrfachauswahl, inkl. „dieser Server“), Projekt, Status
  (inkl. „nur offene“), Art. Dazu ein Suchfeld über die Titel.
- Je Instanz ein Hinweis, wenn sie länger als zwei Intervalle nichts geschickt hat:
  „nicht aktuell – zuletzt gesehen am …“
- Klick öffnet die Detailansicht: Metadaten, Volltext live vom Ursprung (mit
  Ladeanzeige), bei Offline-Ursprung der Snapshot und „zuletzt gesehen am …“.
  Nur lesen, kein Bearbeiten.

**Auf dem Client**: Abschnitt „Katalog-Sync“
- Schalter Sync an/aus, Hub (Name aus `federation_peers`, Link zum Server-Reiter),
  Intervall, Nutzerauswahl, ausgeschlossene Projekte
- Status: letzter erfolgreicher Push, letzter Fehler (z. B. „Hub nimmt noch nicht
  an“), Knopf „Jetzt abgleichen“

**Reiter „Server“**, je Partner: Schalter „Als Hub verwenden“ (Client-Sicht) und
„Katalog annehmen“ (Hub-Sicht) mit Anzahl der Einträge.

Texte über i18n (`federation.json` de/en), Hilfe in `help/{de,en}/federation.md`.

## Nicht-Ziele

- **Memory, Datamining, Dateien, Projekte, Sitzungen**: kein Sync. Für Datamining
  gilt weiter die Live-Abfrage aus `instance-identity.md`.
- **Volltext-Sync**: Beschreibungen, Ideentexte, Anmerkungen und Verlauf werden nie
  automatisch übertragen.
- **Bearbeiten über Server**: Der Hub zeigt nur an. Status ändern oder Tasks anlegen
  auf einem anderen Server geht weiter über `ask_agent("<agent>@<server>")`.
- **Agenten-Werkzeug für den Katalog** (z. B. `task_list(server="*")`): später möglich,
  nicht in dieser Spec.
- **Mesh, mehrere Hubs, Hub-Ketten**: genau ein Hub pro Client.
- **Gesamtkatalog auf den Clients** (Entscheidung Till 21.11.): Ein Client wie
  `hydrahome` sieht in dieser ersten Stufe nur seinen eigenen Sync-Status. Es gibt
  keine Live-Abfrage `catalog_query` beim Hub und kein Weiterreichen von Volltext
  über Dritte. Das kann später nachgezogen werden.
- **Kopplung ohne Tailscale** über das offene Internet.

## Akzeptanzkriterien

1. `hydrahome` und `hydrahive-vps` sind wie bisher gekoppelt. Auf `hydrahome` wird
   der VPS als Hub markiert, ein zweiter Hub lässt sich nicht gleichzeitig setzen.
2. Ohne `enabled`, ohne Nutzerauswahl oder ohne `catalog_accept` auf dem Hub kommt
   kein einziger Eintrag am Hub an. Der Client zeigt den Grund an.
3. Mit allen Schaltern an: Eine neue Idee auf `hydrahome` erscheint innerhalb von
   höchstens 15 s im Katalog des Hubs mit Instanz `hydrahome` (Event-Push).
4. Event-Push abgeschaltet bzw. Hub kurz offline: Die Änderung kommt spätestens
   beim nächsten Timer-Lauf an (≤ 5 min nach Wiederkehr des Hubs).
5. Ein auf dem Client gelöschter Task verschwindet vom Hub, sofort per Event oder
   spätestens beim stündlichen Abgleich.
6. In `federation_catalog_items` stehen nur Metadaten. Weder `description` noch
   `body` noch Anmerkungen werden gespeichert, solange niemand den Eintrag öffnet.
7. Detailansicht auf dem Hub lädt die Beschreibung live vom Client. Ist der Client
   aus, kommt nach ≤ 10 s Snapshot bzw. Metadaten mit „zuletzt gesehen am …“.
8. Gefälschte Signatur, falsche oder alte `seq`, abgelaufene Nachricht,
   `catalog_fetch` von einem Partner, der nicht Hub ist (nach außen `404`) → abgelehnt
   und mit Grund im Audit.
8a. Eine Idee und ein Task, die in derselben Sekunde geändert werden, und zwei
    Änderungen desselben Tasks in derselben Sekunde kommen alle am Hub an (Test für
    das Cursor-Verfahren).
9. `/api/peering/catalog/*` von außerhalb des Tailnets → 403.
10. Einträge aus einem ausgeschlossenen Projekt und von nicht ausgewählten Nutzern
    erscheinen nie am Hub und sind auch per Fetch nicht abrufbar.
11. Auf `hydrahive-vps` sieht `till` die Einträge von till@hydrahome, ein anderer
    Nutzer sieht sie nicht. Admins sehen alle.
12. Partner entfernen → seine Katalog-Einträge auf dem Hub sind weg.
    Partner sperren → keine Annahme mehr.
13. Regression: Aufträge über `ask_agent("<agent>@<server>")`, die Tools
    `task_*`/`idea_*` und die Datamining-Abfrage laufen unverändert. Ist der Katalog
    aus, entsteht kein Netzverkehr.

## Etappen

1. **Datenmodell + Hub-Markierung**: Migration, `is_hub`/`catalog_accept`,
   Einstellungs-Routen, Schalter im Reiter „Server“, Abschnitt „Katalog-Sync“ auf dem
   Client (noch ohne Versand).
2. **Katalog-Quellen**: `register_catalog_source` und `catalog_changed` in
   `ModuleContext`, Anmeldung in den Modulen `tasks` und `scratchpad` (eigener PR im
   Modul-Repo, abwärtskompatibel: ältere Kerne ohne die Methode ignorieren es).
3. **Sync**: `catalog_push` (Timer, Event-Push mit Bündelung, Abgleich gelöschter
   Einträge, `seq`/Ack, Rate-Limit, Audit), Annahme und Upsert auf dem Hub.
4. **Katalog-Ansicht + Nachladen**: Reiter „Katalog“ (Liste, Filter, Suche),
   `catalog_fetch` mit signierter Antwort, Snapshot, Offline-Anzeige.
5. **Live-Abnahme** `hydrahome` ↔ `hydrahive-vps` (Akzeptanzkriterien 1–13).

Abhängigkeit: Der Herkunfts-Instanzname ist der Partnername in `federation_peers`.
Dieser Name kommt schon heute aus dem Kopplungscode. Mit Etappe 1 von
`instance-identity.md` wird `instance_name` dort vorgeschlagen. Der Katalog braucht
diese Etappe nicht zwingend, profitiert aber von einheitlichen Namen.

## Entscheidungen (Till, 21.11.2026)

1. **Hub ist `hydrahive-vps`** (100.89.239.63), der schon gekoppelte und getestete
   VPS. Kein neuer vServer.
2. **Nutzer-Zuordnung über Servergrenzen: gleicher Nutzername reicht**
   (till@hydrahome = till@hydrahive-vps). Das gilt auch für die gleichlautende offene
   Frage in `instance-identity.md` (Datamining), die dort nachzutragen ist.
3. **Snapshot des zuletzt geöffneten Volltexts darf auf dem Hub bleiben**
   (`snapshot_body`, siehe Ablauf 4).
4. **Clients sehen den Gesamtkatalog nicht** (keine Live-Abfrage beim Hub). Das bleibt
   Nicht-Ziel dieser ersten Stufe und kann später folgen.

Offene Fragen gibt es derzeit keine.

## Hinweis für den Review

`instance-identity.md` ist **noch nicht auf main** (Branch `docs/instance-identity`).
Diese Spec übernimmt von dort nur die Namenskonvention (`hydrahome`,
`hydrahive-vps`) und grenzt sich von der Datamining-Entscheidung ab. Technisch hängt
sie nicht davon ab: Der Herkunfts-Instanzname ist der Partnername in
`federation_peers`, den es schon gibt.
