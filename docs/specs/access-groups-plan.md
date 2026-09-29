# Plan: Freigaben und Gruppen — Etappe 1 (Funktions-Freigaben)

**Stand: 29.09.2026 — Plan, noch keine Umsetzung.**
Verbindliche Grundlage: `docs/specs/access-groups.md` (PR #463). Task 5760df8d.

## Ziel

Nach Etappe 1 gilt:
- Der Admin legt Gruppen an und gibt Funktionen an Alle, Gruppen oder einzelne Nutzer frei.
- Nicht freigegebene Funktionen sind für Nicht-Admins gesperrt: in der Schnittstelle
  (403), im Menü (ausgeblendet), auf der Seite („Kein Zugriff“) und für ihre Agenten
  (Werkzeug wird nicht angeboten und bei Aufruf abgelehnt).
- Bestehende Installationen verhalten sich wie vorher, außer bei den heiklen
  Funktionen aus Spec §12. Die sind danach nur für Admins.

Nicht in Etappe 1: Teilen einzelner Sachen (Etappe 2), Kontingente, Anbindung von
Tickets-Teams und Haushalten, Stufe „read“.

## Lieferstrategie

Fünf PRs, jeder für sich lauffähig und grün. Kein PR ändert Verhalten für Admins.

| PR | Inhalt | Verhalten danach |
|---|---|---|
| P1 | Datenmodell, Service, Prüf-Funktion | nichts sichtbar, nur Grundlage + Tests |
| P2 | Admin-API + Oberfläche für Gruppen und Freigaben | Admin kann verwalten, noch ohne Wirkung |
| P3 | Durchsetzung in Schnittstellen (Module + Core) | 403 für Nicht-Freigegebene |
| P4 | Durchsetzung bei Agenten-Werkzeugen | Werkzeuge gefiltert |
| P5 | Menü, Seiten-Sperre, Übergang, Modul-Manifeste | für Nutzer sichtbar, heikle Funktionen admin_only |

Reihenfolge ist Pflicht: P3 und P4 wirken erst, wenn Funktionen angemeldet sind.
Bis P5 meldet niemand welche an, deshalb ändern P3 und P4 allein noch nichts im
Betrieb. Erst P5 schaltet scharf. So lässt sich jeder PR einzeln deployen.

## Dateien

### Backend (neu)
- `core/src/hydrahive/db/migrations/050_access_groups.sql` — Tabellen aus Spec §6
  ohne `access_resource_shares` (kommt in Etappe 2).
- `core/src/hydrahive/access/__init__.py` — öffentliche Funktionen.
- `core/src/hydrahive/access/capabilities.py` — Katalog: Core-Funktionen + aus
  Manifesten gesammelte Modul-Funktionen, Zuordnung Werkzeug → Funktion.
- `core/src/hydrahive/access/store.py` — Datenzugriff Gruppen, Mitglieder, Freigaben, Audit.
- `core/src/hydrahive/access/check.py` — `can_use(user_id, role, capability)`,
  `capabilities_for(user_id, role)`, Cache pro Anfrage.
- `core/src/hydrahive/access/deps.py` — FastAPI-Dependency `require_capability(cap)`.
- `core/src/hydrahive/access/bootstrap.py` — Anfangs-Freigaben nach Spec §11/§12.
- `core/src/hydrahive/api/routes/access_admin.py` — Gruppen + Freigaben (nur Admin).
- `core/src/hydrahive/api/routes/access_me.py` — `GET /api/access/me`.

### Backend (geändert)
- `modules/manifest.py` — Feld `capabilities` lesen und prüfen.
- `tools/base.py` — Feld `module_id: str = ""` am Tool.
- `api/lifespan.py` — beim Registrieren `module_id` setzen, Katalog aufbauen, Bootstrap.
- `api/main.py` — `mount_module_routers()` hängt `require_capability("module.<id>")` an.
- `api/routes/vms_*.py`, `containers_*.py`, `federation.py` — Router-Dependency.
- `runner/runner.py` — nach `scope_tools()` Werkzeuge ohne Freigabe entfernen.
- `runner/dispatcher.py` — zweite Prüfung vor der Ausführung.
- `tools/ask_agent.py` — Föderations-Zweig prüft `core.federation`.
- `api/routes/users.py` — `delete_user()` räumt Mitgliedschaften und Freigaben auf.

`runner.py` hat 406 Zeilen und `main.py` 244. Dort nur Aufrufe einfügen, die Logik
liegt in `access/`. Keine neue Datei über ~200 Zeilen.

### Frontend (neu)
- `frontend/src/features/access/api.ts`, `types.ts`
- `frontend/src/features/access/useAccess.ts` — lädt `/api/access/me` einmal pro Sitzung.
- `frontend/src/features/access/GroupsSection.tsx` — Reiter „Gruppen“ im Benutzer-Overlay.
- `frontend/src/features/access/GrantsOverlay.tsx` — Freigabe-Tabelle.
- `frontend/src/features/access/NoAccess.tsx` — Seite „Kein Zugriff“.
- `frontend/src/features/profile/MyAccessSection.tsx` — „Meine Freigaben“, eingebunden in `ProfilePage.tsx`.

### Frontend (geändert)
- `shared/nav-config.ts` — Filter um Funktionen erweitern.
- `App.tsx` — Modul-Routen in `NoAccess` hüllen, wenn nicht freigegeben.
- `features/cockpit/AdminCockpitPage.tsx` + `admin/adminOverlayRegistry.ts` — Karte „Freigaben“.
- `features/cockpit/admin/UsersOverlay.tsx` — Reiter „Gruppen“.
- `features/agents/_ToolsTab.tsx` bzw. `ToolsSelector.tsx` — gesperrte Werkzeuge ausgegraut.
- `i18n/locales/{de,en}/access.json` — alle Texte.

### Modul-Repo (P5)
- `homeassistant`, `voice`, `archiver`, `opentor`: `capabilities` im Manifest + Patch-Bump.

## Implementierungsreihenfolge

Jeder Task: Test schreiben → RED → minimale Umsetzung → GREEN → Commit.
Tests laufen gegen die isolierte Test-DB (`core/tests/_isolation.py`), Abschluss
jedes PRs mit voller Suite und `leak=0`.

### P1 — Datenmodell, Service, Prüfung

**Task 1.1: Migration**
- Test `tests/test_access_migration.py`: nach `apply_migrations` existieren
  `access_groups`, `access_group_members`, `access_capability_grants`,
  `access_audit`, und die CHECK-Constraints lehnen `subject_type='foo'` und
  `level='owner'` ab.
- Umsetzung: `050_access_groups.sql`.

**Task 1.2: Gruppen-Store**
- Test `tests/test_access_store_groups.py`: anlegen, doppelter Name → Fehler,
  umbenennen, Mitglied hinzufügen/entfernen (idempotent), löschen entfernt
  Mitglieder (CASCADE), `groups_of(user_id)`.
- Umsetzung: `access/store.py` Teil Gruppen.

**Task 1.3: Freigabe-Store + Audit**
- Test `tests/test_access_store_grants.py`: `grant(cap, subject, level, actor)`
  legt an bzw. ändert Stufe, `revoke` entfernt, `grants_for(cap)`, jede Änderung
  erzeugt genau einen Audit-Eintrag mit Akteur.
- Umsetzung: `access/store.py` Teil Freigaben + Audit.

**Task 1.4: Katalog**
- Test `tests/test_access_capabilities.py`:
  - Core-Funktionen `core.vms`, `core.containers`, `core.federation` sind bekannt.
  - `register_module(manifest)` übernimmt `capabilities`, ergänzt fehlendes
    `module.<id>` automatisch.
  - `capability_for_tool("ha_call_service")` → `homeassistant.control`, wenn im
    Manifest unter `tools` zugeordnet, sonst `module.<id>`.
  - Unbekannte Funktion → `is_declared()` False.
- Umsetzung: `access/capabilities.py`.

**Task 1.5: Prüfung**
- Test `tests/test_access_check.py` (Tabelle aus Spec §7):
  - Admin darf alles, auch ohne Einträge.
  - Nicht deklarierte Funktion → erlaubt.
  - Deklariert, keine Freigabe → verboten.
  - Freigabe `everyone` → erlaubt; Nutzer direkt → erlaubt; Gruppe, in der er ist
    → erlaubt; Gruppe, in der er nicht ist → verboten.
  - Höchste Stufe gewinnt (`use` über Gruppe + `manage` direkt → `manage`).
  - DB-Fehler (Store wirft) → verboten + Log (fail-closed).
- Umsetzung: `access/check.py`.

**Task 1.6: Manifest-Feld**
- Test in `tests/test_module_manifest.py` (erweitern): `capabilities` wird gelesen,
  ungültige `id` (nicht `module.<id>` oder `<id>.x`), ungültiges `default` →
  Ladefehler mit klarer Meldung; altes `permissions` wird weiter akzeptiert.
- Umsetzung: `modules/manifest.py`.

**P1 fertig:** volle Suite grün, `leak=0`, ruff sauber, PR.

### P2 — Admin-Verwaltung

**Task 2.1: Admin-API Gruppen**
- Test `tests/test_access_admin_routes.py`: Nicht-Admin → 403 auf alle Routen;
  Admin: `GET/POST /api/access/groups`, `PATCH/DELETE /api/access/groups/{id}`,
  `PUT/DELETE /api/access/groups/{id}/members/{user_id}`; unbekannter Nutzer → 404.
- Umsetzung: `api/routes/access_admin.py` mit `require_admin_principal`.

**Task 2.2: Admin-API Freigaben**
- Test (gleiche Datei): `GET /api/access/capabilities` (Katalog + aktuelle
  Freigaben), `PUT /api/access/grants` setzt, `DELETE` entfernt; unbekannte
  Funktion → 400; Audit-Eintrag vorhanden.
- Umsetzung: `access_admin.py`.

**Task 2.3: `/api/access/me`**
- Test `tests/test_access_me.py`: liefert für Admin `{"admin": true}`, für Nutzer
  die Liste erlaubter deklarierter Funktionen mit Stufe und seine Gruppen.
- Umsetzung: `access_me.py`.

**Task 2.4: Nutzer löschen räumt auf**
- Test `tests/test_access_user_delete.py` (neu): Nutzer in Gruppe + mit
  Freigabe löschen → keine Zeilen mehr mit seiner `user_id`, Audit-Eintrag.
- Umsetzung: `users.py → delete_user()` ruft `access.store.purge_user(user_id)`.

**Task 2.5: Oberfläche**
- Test (vitest) `GroupsSection.test.tsx`: Liste rendert, Anlegen ruft API,
  Fehler wird angezeigt. `GrantsOverlay.test.tsx`: Zelle umschalten ruft
  `PUT /grants` mit richtigem Subjekt.
- Umsetzung: Reiter „Gruppen“ im `UsersOverlay`, Karte „Freigaben“ im
  Admin-Cockpit, i18n de/en.

**P2 fertig:** Suite + Frontend-Build grün, PR.

### P3 — Durchsetzung in Schnittstellen

**Task 3.1: `require_capability`**
- Test `tests/test_access_deps.py`: Dependency liefert 403 `capability_denied`
  mit Funktion im Fehler, lässt Admin und Freigegebene durch, API-Key (`hhk_`)
  wird wie sein Nutzer behandelt.
- Umsetzung: `access/deps.py` auf Basis `require_principal`.

**Task 3.2: Modul-Router-Gate**
- Test `tests/test_access_module_gate.py` mit `make_module`/`mod_env`:
  Modul mit `capabilities` und ohne Freigabe → 403 für Nutzer, 200 für Admin;
  Modul ohne `capabilities` → 200 für alle (Kompatibilität).
- Umsetzung: `mount_module_routers()` → `dependencies=[Depends(require_capability(f"module.{id}"))]`.

**Task 3.3: Core-Gate VMs, Container, Föderation**
- Test `tests/test_access_core_gate.py`: mit angemeldeter Funktion und ohne
  Freigabe → `POST /api/vms`, `POST /api/containers`, `GET /api/federation/workstations`
  → 403; mit Freigabe → wie bisher. Solange `core.*` nicht angemeldet ist (vor
  P5-Bootstrap) → wie bisher.
- Umsetzung: Router-Dependency in den genannten Dateien.

**Task 3.4: Föderation im Werkzeug**
- Test `tests/test_ask_agent_federation_access.py` (neu): Aufruf
  `persona@workstation` durch Agent eines Nutzers ohne `core.federation`
  → `ToolResult.fail` mit klarer Meldung, kein Netzaufruf.
- Umsetzung: `_execute_federated(target, task, args)` bekommt heute kein `ctx`.
  Signatur um `ctx` erweitern (Aufruf in `ask_agent.py` Zeile ~107) und dort zuerst
  prüfen. `ctx.user_id` ist heute der Username (sessions speichern Namen) → über
  `get_by_username()` zur stabilen ID auflösen.

**P3 fertig:** Suite grün, PR.

### P4 — Durchsetzung bei Werkzeugen

**Task 4.1: Filter im Lauf**
- Test `tests/test_access_runner_tools.py`: Agent mit `ha_call_service` in der
  Liste, Besitzer ohne Freigabe → Schema nicht in `tool_schemas`, nicht in
  `allowed_tools`; Admin-Besitzer → vorhanden.
- Umsetzung: in `runner.py` nach `scope_tools()` ein Aufruf
  `access.filter_tools(owner, local_tools)`. Logik in `access/check.py`.

**Task 4.2: Zweite Prüfung im Dispatcher**
- Test in `tests/test_dispatcher_authz.py` (erweitern): Werkzeug steht in
  `allowed_tools`, Besitzer hat die Funktion nicht → `ToolResult.fail`
  „keine Freigabe“, Status `error` persistiert.
- Umsetzung: `dispatcher.execute_tool()` vor der Ausführung.

**Task 4.3: Agent-Editor zeigt Sperren**
- Test (vitest): gesperrtes Werkzeug ausgegraut mit Hinweis „Keine Freigabe für
  den Besitzer“.
- Umsetzung: Agent-Editor nutzt `/api/access/me` des Besitzers
  (neuer Admin-Endpunkt `GET /api/access/users/{id}/capabilities` für fremde Agenten).

**P4 fertig:** Suite grün, PR.

### P5 — Sichtbar machen und scharf schalten

**Task 5.1: Menü-Filter**
- Test (vitest) `nav-config.test.ts`: Eintrag mit `capability`, die fehlt → nicht
  sichtbar; Admin → sichtbar; Eintrag ohne `capability` → sichtbar.
- Umsetzung: Nav-Einträge bekommen optional `capability`, Modul-Nav erhält
  automatisch `module.<id>`.

**Task 5.2: Seiten-Sperre**
- Test (vitest): Modul-Route ohne Freigabe rendert `NoAccess`, nicht die Seite.
- Umsetzung: `App.tsx`.

**Task 5.3: Bootstrap / Übergang**
- Test `tests/test_access_bootstrap.py`:
  - Erster Lauf auf leerer Tabelle: jede deklarierte Funktion mit
    `default: everyone` bekommt `everyone`, `admin_only` bekommt nichts.
  - Zweiter Lauf ändert nichts (idempotent, Marker in `access_audit`).
  - Vom Admin entfernte `everyone`-Freigabe wird beim nächsten Start NICHT neu angelegt.
  - Neu installiertes Modul: seine Funktionen werden beim ersten Laden nach
    `default` angelegt, bestehende bleiben unberührt.
- Umsetzung: `access/bootstrap.py`, Aufruf in `lifespan.py` nach Modul-Load.

**Task 5.4: Core-Funktionen anmelden**
- Test: `core.vms`, `core.containers`, `core.federation` sind im Katalog mit
  `admin_only`. Nach Bootstrap: Nutzer → 403 auf `POST /api/vms`.
- Umsetzung: `access/capabilities.py`.

**Task 5.5: Modul-Manifeste** (Modul-Repo, eigener PR)
- `homeassistant`: `module.homeassistant` (everyone), `homeassistant.control`
  (admin_only, tools `ha_call_service`).
- `voice`: `module.voice` (admin_only).
- `archiver`: `module.archiver` (admin_only).
- `opentor`: `module.opentor` (admin_only).
- Je Patch-Bump in `manifest.json` (CI `check_version_bump.py`), Tests mitziehen.

**Task 5.6: Hinweis im Admin-Cockpit**
- Test (vitest): Nach Bootstrap mit admin_only-Funktionen zeigt das Cockpit
  einmalig den Hinweis mit Link zur Freigabe-Tabelle, „Verstanden“ blendet aus.
- Umsetzung: `GET /api/access/notice` + Karte im Admin-Cockpit.

**Task 5.7: Hilfe und Handbuch**
- `frontend/src/i18n/help/de|en/access.md` (neu), Hinweise in
  `homeassistant.md`, `vms.md`, `federation.md`.
- Discord-Handbuch: neuer Beitrag „Freigaben & Gruppen“ + Inhaltsverzeichnis ergänzen,
  „Gut zu wissen“ in HA/Voice/VMs/Föderation/Archiver/OpenTor anpassen (beide Server).

**P5 fertig:** Suite + Build grün, Security-Review (Skill `security-audit`),
Deploy durch Till, Live-Probe mit einem Nicht-Admin-Konto.

## Akzeptanzkriterien Etappe 1

Übernommen aus Spec §16, zusätzlich:
- [ ] Jeder PR für sich grün und deploybar, Admin-Verhalten unverändert.
- [ ] Live nach P5: joshua22 sieht Home Assistant, kann aber nicht schalten;
      sein Buddy bekommt `ha_call_service` nicht; VMs, Container, Föderation,
      Voice, Archiver, OpenTor fehlen im Menü und liefern 403.
- [ ] Freigabe `homeassistant.control` an Gruppe „Familie“ mit joshua22 →
      Schalten geht, ohne Neustart.
- [ ] Alle Tests gegen isolierte DB, `leak=0`.

## Risiken

- **Performance:** Jede Anfrage prüft Funktionen. Gegenmittel: Cache pro Anfrage,
  Katalog im Speicher, Index auf `access_capability_grants(capability)`.
- **Aussperren:** Admins sind nie betroffen, der letzte Admin kann nicht
  herabgestuft werden (gibt es schon). Bootstrap legt nie Sperren für Funktionen
  an, die nicht ausdrücklich `admin_only` sind.
- **Username vs. user_id:** Sessions und `ctx.user_id` speichern heute den Namen.
  Die Prüfung löst immer über `get_by_username()` zur stabilen ID auf.
- **Module-Updates:** Ein Modul, das später `capabilities` ergänzt, darf bestehende
  Nutzung nicht still sperren → Default für nachträglich angemeldete Funktionen ist
  `everyone`, außer das Modul setzt ausdrücklich `admin_only` (dann Hinweis im Cockpit).

## Nicht in diesem Plan
- Teilen einzelner Sachen (Etappe 2, eigener Plan).
- Kontingente für VMs/Container.
- Rückfrage bei kritischen Home-Assistant-Domains (eigener Fix in 1333b295).
- Blueprint-Agenten-Werkzeug (9111b283).
