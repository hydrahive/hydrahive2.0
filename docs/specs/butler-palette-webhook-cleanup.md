# Fix-Spec: Butler — Palette gegen Registry, Webhook benutzbar machen

> **Status:** Freigegeben (Till, 2026-09-28)
> **Ziel:** Die Butler-Oberfläche bietet nur Bausteine an, die der Server ausführen
> kann, und der Server nimmt nur solche an. Der Projekt-Webhook wird ohne
> Dateizugriff benutzbar: richtige URL im Knoten, Secret im Cockpit einsehbar.
> **Tasks:** a254d069 (Palette/Registry), 6f6463ae (Webhook)

## 1. Befund (28.09.2026, gegen `main` 04464bfc geprüft)

### Palette und Registry
- Die Palette (`frontend/src/features/butler/palette-data.ts`) bietet 13 Bedingungen
  an. Die Server-Registry (`core/src/hydrahive/butler/registry/conditions/`) kennt 4
  davon. Ohne Gegenstück: `contact_known`, `git_branch_is`, `git_author_is`,
  `git_action_is`, `email_from_contains`, `email_subject_contains`,
  `email_body_contains`, `discord_event_is`, `discord_emoji_is`.
  Trifft der Executor auf so eine Bedingung, schreibt er `unknown_condition` in den
  Trace und beendet den Pfad still (`executor.py:72-76`).
- Die Aktionen `send_email`, `git_create_issue`, `git_add_comment`, `discord_post`
  sind Stubs (`_stub.py`): nur Log-Eintrag, aber `ok=True`. Die Palette markiert nur
  Trigger als „bald“ (`UNWIRED_TRIGGERS`), nicht diese Aktionen.
- Der Server kennt Bausteine, die die Palette nicht anbietet: Trigger `cron_fired`
  (mit laufendem Scheduler) und Bedingung `regex_match`. Beide funktionieren.
- `POST/PUT /api/butler/flows` prüft Subtypes nicht gegen die Registry.
- Feldname-Drift bei `http_post`: die UI speichert den Body als `body_template`
  (`_actions.tsx:44`, `defaultParams`), der Server liest `body`
  (`http_post.py:24`). Der Body kommt nie an, der Server sendet einen leeren Body.

### Webhook
- Der Knoten „Webhook empfangen“ zeigt `${origin}/webhooks/butler/<hook_id>`.
  Diese Route gab es nie. Echte Route: `POST /api/butler/webhooks/project/{project_id}`.
- `hook_id` wird mit `event.channel = "project:<id>"` verglichen
  (`webhook_received.py:13`). Die UI säubert die Eingabe auf `[a-z0-9_-]`, ein
  Doppelpunkt überlebt das nicht. Das Feld hat nie gepasst; nur leer funktioniert.
- `webhook_secret` wird pro Projekt erzeugt (`projects/config.py:55`) und vom
  Endpoint verlangt (`X-Webhook-Secret`), ist aber nirgends einsehbar
  (`public_view.py` liefert nur `has_webhook_secret`).

## 2. Scope

### A. Server: Registry-Prüfung beim Speichern
- Neue Funktion `unknown_subtypes(flow) -> list[str]` in
  `core/src/hydrahive/butler/registry/_validation.py`: sammelt alle Knoten, deren
  `subtype` in der jeweiligen Registry (TRIGGERS/CONDITIONS/ACTIONS) fehlt.
- `create_flow` und `update_flow` lehnen mit `400 butler_subtype_unknown`
  (`params={"subtypes": "a, b"}`) ab. Modul-Subtypes sind erlaubt, weil sie in
  denselben Registries stehen (`modules/butler_bridge.py`).
- Bestehende gespeicherte Flows werden **nicht** angefasst. Laden und Ausführen
  bleiben tolerant (Trace `unknown_condition`/`unknown_action`), zusätzlich ein
  `logger.warning` beim Executor, damit es im Log sichtbar ist.

### B. Server: Webhook-Trigger ohne Hook-ID
- `webhook_received` verliert den Parameter `hook_id`. Der Matcher prüft nur noch
  `event_type == "webhook"`. Alte Flows mit gesetztem `hook_id` laden weiter; das
  Feld wird ignoriert.
- Die Beschreibung des Triggers nennt die echte Route.

### C. Server: Secret einsehbar und rotierbar
- Neue Datei `core/src/hydrahive/api/routes/projects_webhook.py`:
  - `GET /api/projects/{id}/webhook` → `{url_path, secret}`; nur Projekt-`admin`
    (oder System-Admin) via `check_project_access(required="admin")`.
  - `POST /api/projects/{id}/webhook/rotate` → neues Secret, gleiche Antwort,
    Audit-Eintrag `webhook_secret_rotated` (ohne Wert).
- Projekte ohne Secret (2 Altbestände) bekommen beim ersten `GET` keins
  automatisch; `rotate` erzeugt eins. So bleibt das Verhalten explizit.
- `public_view.py` bleibt unverändert: `has_webhook_secret` reicht für die
  Projektliste.

### D. Frontend: Palette bereinigen
- Die 9 Bedingungen ohne Server-Gegenstück werden aus `PALETTE_STRUCTURE`,
  `PALETTE_LABEL_KEY`, `defaultParams`, `paramSummary.ts` und
  `properties/registry.tsx` entfernt. Die Formulare in `_conditions.tsx`
  verschwinden mit. Gleiches für die passenden Trigger `git_event_received`,
  `discord_event_received`, `email_received` (sie sind heute schon gesperrt und
  hätten ohne Bedingungen keinen Sinn) — `UNWIRED_TRIGGERS` entfällt.
- Stub-Aktionen `send_email`, `git_create_issue`, `git_add_comment`,
  `discord_post` bekommen die „bald“-Sperre (neues Set `UNWIRED_ACTIONS`), bleiben
  aber sichtbar, weil sie als Nächstes echt werden (Task c7ba81e9, 9f8429f3).
  Speichern mit so einer Aktion wird im Frontend wie bei Triggern blockiert.
- Neu in der Palette: Trigger `cron_fired` (Feld Cron-Ausdruck, Platzhalter
  `0 8 * * *`, Hinweis: UTC), Bedingung `regex_match` (Feld Muster; Ziel bleibt
  Nachrichtentext).
- `http_post`: das Formular schreibt `body`, wie der Server es liest. Alte Flows
  mit `body_template` werden beim Laden in `adapter.ts` auf `body` umgeschrieben.
- Das Sperr-Toast beim Speichern wird über i18n ausgegeben (heute hartkodiert
  deutsch, `useButlerFlow.ts:62`).

### E. Frontend: Webhook-Knoten und Cockpit
- `_webhook.tsx`: Feld Hook-ID entfällt. Ohne Projekt-Kontext (`?project=` fehlt)
  steht dort der Hinweis, dass der Flow im Projekt-Cockpit über „Butler“ geöffnet
  werden muss. Mit Projekt-Kontext: echte URL mit Kopierknopf und ein Hinweis auf
  den Header `X-Webhook-Secret` mit Verweis auf Cockpit → Integrationen.
- `ProjectIntegrationsPanel.tsx` bekommt einen Abschnitt „Webhook“ (nur wenn der
  Nutzer Projekt-Admin ist, also `GET …/webhook` 200 liefert): URL, Secret
  (verdeckt, Auge-Knopf, Kopieren), Knopf „Neu erzeugen“ mit Bestätigung.
- `_OverviewTab.tsx` (Einstellungen → Projekte) zeigt weiterhin nur die URL.

### Nicht in Scope
- Heartbeat/Cron-Antwortaktionen (Task 35aa665d, Option (a) beschlossen).
- Stubs echt machen (Task c7ba81e9).
- Umlaute in `butler.json` (Doku-Task 16dc5567).
- Frontend-Tests (es gibt keine Testinfrastruktur im Frontend).

## 3. Sicherheit
- Secret nur für Projekt-Admins lesbar; Mitglieder mit `read`/`write` bekommen 403.
- Rotation schreibt einen Audit-Eintrag ohne den Wert.
- Der Secret-Wert taucht in keinem Log, keiner Tool-Antwort und nicht in der
  Projektliste auf.
- Der Webhook-Endpoint selbst bleibt unverändert (Secret-Vergleich mit
  `secrets.compare_digest`, Tenant-Isolation über `_project_flows`).

## 4. Tests (TDD, Testnamen deutsch)
- `test_butler_subtype_validation.py`: unbekannte Bedingung → 400 mit Subtype im
  Fehler; bekannte Bausteine → 201; Modul-Subtype (in Registry eingetragen) → 201;
  PUT verhält sich wie POST; Executor loggt Warnung bei unbekannter Bedingung.
- `test_butler_webhook_trigger.py`: Trigger passt auf jedes `webhook`-Event, auch
  mit altem `hook_id`-Param; passt nicht auf `message`.
- `test_project_webhook_routes.py`: Admin sieht Secret; Mitglied `write` → 403;
  Fremder → 403; Rotation ändert Secret und schreibt Audit; Rotation erzeugt Secret
  bei Alt-Projekt ohne; Projektliste enthält den Wert nicht.

## 5. Nacharbeit
- Discord-Beitrag Butler (1554107584422875156): „Noch nicht fertig“-Block kürzen,
  Cron und Regex in die Liste der funktionierenden Bausteine.
- Hilfeartikel `butler.md` (Doku-Task 16dc5567).
