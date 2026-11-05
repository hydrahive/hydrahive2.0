# Plan: Sessionliste paginieren und interne Handoffs ausblenden

## Ziel

Die normale Chatliste zeigt für den angemeldeten Nutzer alle relevanten Benutzerchats seitenweise an. Interne AgentLink-Handoff-Sessions verdrängen keine Projektagenten-Chats mehr. Bewusst wiederhergestellte Sessions mit `metadata.user_visible=true` bleiben sichtbar. Der bestehende Endpoint `GET /api/sessions` bleibt rückwärtskompatibel.

## Designentscheidungen

- Neuer Endpoint `GET /api/sessions/page` statt Breaking Change an `GET /api/sessions`.
- Antwort: `{items, total, limit, offset, has_more}`.
- Grenzen: `limit` 1–200, `offset` ≥ 0.
- Normalansicht: Session ist sichtbar, wenn kein `agent_handoffs.session_id` existiert **oder** `metadata.user_visible=true` gesetzt ist.
- `include_internal=true` ist für technische Ansichten möglich, bleibt aber auf Sessions des authentifizierten Nutzers beschränkt.
- Optionaler Projektscope: `project_id=<id>` oder `unassigned=true`; beide gleichzeitig sind ungültig.
- Der Browser lädt 50 Einträge je Seite und bietet „Mehr laden“ an.
- Seiten werden nach `updated_at DESC, id DESC` sortiert und clientseitig nach ID dedupliziert.
- Deep-Link-/Einzelsession-Zugriff bleibt über den bestehenden eigentümergeprüften Einzelendpoint möglich.

## Dateien

### Backend

- `core/src/hydrahive/db/migrations/056_agent_handoffs_session_index.sql` — Index für den Sichtbarkeitsfilter.
- `core/src/hydrahive/db/session_pages.py` — paginierte, benutzer- und projektspezifische Abfrage plus Gesamtzahl.
- `core/src/hydrahive/api/routes/sessions.py` — neuer authentifizierter `/page`-Endpoint und Query-Validierung.
- `core/tests/test_session_list_page.py` — API-, Auth-, Filter-, Pagination- und Grenztests.

### Frontend

- `frontend/src/features/chat/types.ts` — `SessionPage`.
- `frontend/src/features/chat/api.ts` — paginierter API-Client und bestehender Einzelabruf.
- `frontend/src/features/chat/_sessionPages.ts` — pure Merge-/Deduplizierungslogik.
- `frontend/src/features/chat/_sessionPages.test.ts` — Merge-, Sortier- und Deduplizierungstests.
- `frontend/src/features/chat/ChatPane.tsx` — initiale Seite, Refresh-Merge und „Mehr laden“.
- `frontend/src/features/chat/SessionList.tsx` — Ladeaktion und Gesamtanzeige.
- `frontend/src/features/chat/SessionList.test.tsx` — sichtbare Ladeaktion und Disabled-Zustand.
- `frontend/src/i18n/locales/de/chat.json` und `en/chat.json` — Texte.

## Implementierungsreihenfolge

### Task 1: Backend-RED

- [ ] `test_page_hides_handoff_sessions_but_keeps_promoted` schreiben.
- [ ] `test_page_is_scoped_to_authenticated_user` schreiben.
- [ ] `test_page_paginates_more_than_50_sessions` schreiben.
- [ ] `test_page_scopes_project_and_unassigned` schreiben.
- [ ] `test_page_rejects_conflicting_scope_and_invalid_bounds` schreiben.
- [ ] Tests ausführen und ROT belegen.

### Task 2: Backend-GREEN

- [ ] Indexmigration ergänzen.
- [ ] `session_pages.list_page_for_user()` mit ausschließlich parametrisierten Queries implementieren.
- [ ] `/api/sessions/page` vor `/{session_id}` registrieren.
- [ ] Bestehenden `/api/sessions`-Endpoint unverändert lassen.
- [ ] Zieltests und relevante Sessiontests grün ausführen.

### Task 3: Frontend-RED

- [ ] Pure Seitenergänzung/Deduplizierung testen.
- [ ] `SessionList` mit „Mehr laden“, Gesamtzahl und Lade-/Disabled-Zustand testen.
- [ ] Tests ROT ausführen.

### Task 4: Frontend-GREEN

- [ ] `SessionPage` und API-Client ergänzen.
- [ ] Projekt-/Unassigned-Scope aus `ChatPane` an API weitergeben.
- [ ] Initial laden, Refresh mit vorhandenen Seiten mergen, weitere Seite anhängen.
- [ ] Neue/gelöschte Sessions lokal korrekt halten.
- [ ] i18n Deutsch/Englisch ergänzen.
- [ ] Zieltests, TypeScript und Frontend-Suite grün ausführen.

### Task 5: Review und Lieferung

- [ ] Security-Audit: Auth vor Query, parametrisierte SQL, keine fremden Sessions.
- [ ] HH-Review: Struktur, Dateigrößen, keine Debugausgaben.
- [ ] Core-Gesamttests, Ruff, TypeScript, Vitest ausführen.
- [ ] Arbeitsbaum und Diff prüfen.
- [ ] Commit, Push und PR; CI abwarten.

## Akzeptanzkriterien

- [ ] Bei 500 internen Handoffs und einem normalen Projektchat erscheint der Projektchat auf der ersten Seite.
- [ ] Interne Handoffs fehlen standardmäßig.
- [ ] `metadata.user_visible=true` macht eine Handoff-Session sichtbar.
- [ ] Ein Nutzer sieht niemals Sessions eines anderen Nutzers.
- [ ] Projektansichten paginieren innerhalb des gewählten Projekts.
- [ ] Direkte Chats ohne Projekt können separat paginiert werden.
- [ ] Mehr als 50 sichtbare Sessions sind über „Mehr laden“ erreichbar.
- [ ] Legacy-Clients von `GET /api/sessions` funktionieren unverändert.
- [ ] Keine Session wird gelöscht oder automatisch umgehängt.

## Nicht in diesem Plan

- Konto-/Instanzanzeige in der Topbar; folgt als separater P0-PR.
- Eigentümermigration weiterer Sessions.
- Datamining-/Buddy-Historienansichten.
- Game-Studio-Implementierung.
